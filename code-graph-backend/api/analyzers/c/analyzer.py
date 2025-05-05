import os
from pathlib import Path
# Убираем subprocess, так как он не используется в упрощенной версии
from api.entities import Entity, File # Предполагаем правильный путь импорта
from typing import Optional, List, Dict, Set # Используем стандартные типы из typing
# В файле: /api/api/analyzers/c/analyzer.py
from ..analyzer import AbstractAnalyzer #  (если AbstractAnalyzer в /api/api/analyzers/analyzer.py)
import tree_sitter_cpp as tscpp
from tree_sitter import Language, Node, Parser
import logging
# Убираем import re, если он не нужен в других частях

logger = logging.getLogger('code_graph')

class CppAnalyzer(AbstractAnalyzer):
    """
    Simplified C++ Analyzer using tree-sitter ONLY.
    Implements AbstractAnalyzer interface BUT without using LSP.
    Symbol resolution across files is unreliable/returns None.
    """
    def __init__(self) -> None:
        CPP_LANGUAGE = Language(tscpp.language())
        # Инициализируем родительский класс с языком
        super().__init__(CPP_LANGUAGE)
        # Парсер уже создается в super().__init__(language)
        # self.parser = Parser() # Этот парсер можно получить из self.parser родительского класса
        # self.parser.set_language(CPP_LANGUAGE)
        self._project_root: Optional[Path] = None # Сохраним корень проекта для is_dependency

    # --- Реализация недостающего абстрактного метода ---
    def is_dependency(self, file_path: str) -> bool:
        """
        (Simplified) Check if the file is considered a dependency.
        Assumes files outside the analyzed project root are dependencies.
        """
        if not self._project_root:
            # Если корень проекта не установлен (например, метод вызван до add_dependencies),
            # считаем, что это не зависимость (или можно вернуть True, в зависимости от логики)
            logger.warning("is_dependency called before project root was set. Assuming False.")
            return False

        try:
            # Преобразуем путь к файлу в абсолютный Path объект
            abs_file_path = Path(file_path).resolve()
            # Проверяем, находится ли файл внутри корня проекта
            # relative_to выбросит ValueError, если путь не внутри
            abs_file_path.relative_to(self._project_root)
            # Если ошибки нет, файл внутри проекта -> не зависимость (в нашей упрощенной логике)
            return False
        except ValueError:
            # Файл находится вне корня проекта -> считаем его зависимостью
            logger.debug(f"File '{file_path}' is outside project root '{self._project_root}'. Considered a dependency.")
            return True
        except Exception as e:
            # Обработка других ошибок, например, некорректный путь
            logger.error(f"Error checking dependency status for '{file_path}': {e}")
            return False # По умолчанию считаем не зависимостью при ошибке

    # --- Реализация остальных абстрактных методов (из предыдущей версии) ---

    def _find_included_file(self, include_path_str: str, current_file_path: Path) -> Optional[Path]:
        """(Helper) Tries to find a local include file within the project root."""
        if not self._project_root:
            return None
        # Логика # В файле: /api/api/analyzers/c/analyzer.py
        from ..analyzer import AbstractAnalyzer # ПРАВИЛЬНО (если AbstractAnalyzer в /api/api/analyzers/analyzer.py)поиска остается прежней...
        path_relative_to_current = (current_file_path.parent / include_path_str).resolve()
        if path_relative_to_current.is_file():
            try:
                 if path_relative_to_current.relative_to(self._project_root):
                    return path_relative_to_current
            except ValueError: pass

        search_dirs = [self._project_root]
        # Добавляем стандартные папки для поиска, если они есть
        potential_include_dir = self._project_root / 'include'
        if potential_include_dir.is_dir():
             search_dirs.append(potential_include_dir)
        potential_src_dir = self._project_root / 'src'
        if potential_src_dir.is_dir():
             search_dirs.append(potential_src_dir)

        for base_dir in search_dirs:
            path_relative_to_root = (base_dir / include_path_str).resolve()
            if path_relative_to_root.is_file():
                 try:
                    if path_relative_to_root.relative_to(self._project_root):
                        return path_relative_to_root
                 except ValueError: pass

        logger.debug(f"Could not find local include '{include_path_str}' starting from {current_file_path}")
        return None

    def add_dependencies(self, path: Path, files: List[Path]):
        """
        Finds local #include "..." directives and adds the referenced files if found
        within the project directory. Ignores system includes <...>.
        """
        self._project_root = path.resolve() # Сохраняем и резолвим корень проекта
        logger.info(f"Scanning for local includes in {self._project_root}. System includes <...> are ignored.")

        known_files_set: Set[Path] = {f.resolve() for f in files}
        queue: List[Path] = [f.resolve() for f in files]
        processed_for_includes: Set[Path] = set()

        include_query = self.language.query("""
            (preproc_include path: (string_literal) @local_include)
        """)

        while queue:
            current_file = queue.pop(0)
            if current_file in processed_for_includes or not current_file.is_file():
                continue
            processed_for_includes.add(current_file)

            logger.debug(f"Scanning for includes in: {current_file}")
            try:
                # Используем парсер из self
                tree = self.parser.parse(current_file.read_bytes())
                captures = include_query.captures(tree.root_node)

                for node, capture_name in captures:
                    if capture_name == 'local_include':
                        include_path_str = node.text.decode('utf-8').strip('"')
                        found_path = self._find_included_file(include_path_str, current_file)

                        if found_path and found_path not in known_files_set:
                            logger.info(f"Found new file via include: {found_path} (from {current_file})")
                            known_files_set.add(found_path)
                            files.append(found_path) # Добавляем в исходный список files
                            if found_path not in processed_for_includes:
                                queue.append(found_path)

            except FileNotFoundError:
                logger.warning(f"File not found during include scan: {current_file}")
            except Exception as e:
                logger.error(f"Error parsing {current_file} for includes: {e}")

        logger.info(f"Include scan complete. Total files to analyze: {len(files)}")


    def get_entity_label(self, node: Node) -> str:
        # Код остается прежним из упрощенной версии
        node_type = node.type
        # Basic declarations
        if node_type == 'class_specifier': return "Class"
        if node_type == 'struct_specifier': return "Struct"
        if node_type == 'union_specifier': return "Union"
        if node_type == 'enum_specifier': return "Enum"
        if node_type == 'namespace_definition': return "Namespace"
        # Functions and Methods
        if node_type == 'function_definition':
            parent = self.find_parent(node, ['class_specifier', 'struct_specifier', 'namespace_definition', 'translation_unit'])
            if parent and parent.type in ['class_specifier', 'struct_specifier']:
                return "Method"
            return "Function"
        if node_type == 'declaration':
            # Check for constructor/destructor
            is_constructor = False
            is_destructor = False
            type_node = node.child_by_field_name('type')
            declarator_node = node.child_by_field_name('declarator')
            if declarator_node and declarator_node.type == 'function_declarator':
                if type_node is None: # Characteristic of constructor/destructor declaration
                    name_node = self._find_name_in_declarator(declarator_node)
                    if name_node:
                        name_text = name_node.text.decode('utf-8')
                        if name_text.startswith('~'):
                            is_destructor = True
                        else:
                            # Check if name matches parent class/struct name
                            class_node = self.find_parent(node, ['class_specifier', 'struct_specifier'])
                            if class_node:
                                class_name_node = class_node.child_by_field_name('name')
                                if class_name_node and class_name_node.text.decode('utf-8') == name_text:
                                    is_constructor = True

            if is_constructor or is_destructor:
                parent = self.find_parent(node, ['field_declaration_list', 'class_specifier', 'struct_specifier', 'namespace_definition', 'translation_unit'])
                if parent and parent.type in ['field_declaration_list', 'class_specifier', 'struct_specifier']:
                    return "Constructor" if is_constructor else "Destructor"

            # Check for function/method declaration (even without definition here)
            if declarator_node and declarator_node.type == 'function_declarator':
                parent = self.find_parent(node, ['field_declaration_list', 'class_specifier', 'struct_specifier', 'namespace_definition', 'translation_unit'])
                if parent and parent.type in ['field_declaration_list', 'class_specifier', 'struct_specifier']:
                    return "Method" # Declaration of a method
                # Check if it's inside a namespace or top-level
                if parent and parent.type in ['namespace_definition', 'translation_unit']:
                    return "Function" # Declaration of a function

        # Other entities
        if node_type == 'field_declaration': return "Field"
        # parameter_declaration is usually not a top-level entity handled here
        if node_type == 'using_declaration': return "Using"
        if node_type == 'type_alias_declaration': return "TypeAlias" # using Name = Type;
        if node_type == 'template_declaration': return "Template"

        raise ValueError(f"Unknown C++ entity type for label: {node_type}")


    def _find_name_in_declarator(self, declarator: Node) -> Optional[Node]:
        # Код остается прежним
        current = declarator
        while current:
            name_node = current.child_by_field_name('declarator')
            if name_node:
                if name_node.type in ['identifier', 'qualified_identifier', 'destructor_name', 'operator_name', 'template_function', 'template_type']: # Added template_type
                    return name_node
                elif name_node.type in ['function_declarator', 'pointer_declarator', 'array_declarator', 'reference_declarator', 'parenthesized_declarator']:
                     current = name_node
                else:
                     logger.debug(f"Stopping name search in declarator at unexpected type: {name_node.type}")
                     return None
            else:
                if current.type in ['identifier', 'qualified_identifier', 'destructor_name', 'operator_name', 'template_function', 'template_type']:
                     return current
                return None
        return None


    def get_entity_name(self, node: Node) -> str:
        # Код остается прежним из упрощенной версии
        name = "[Unknown]"
        name_node: Optional[Node] = None
        node_type = node.type

        try:
            if node_type in ['class_specifier', 'struct_specifier', 'union_specifier', 'enum_specifier']:
                name_node = node.child_by_field_name('name')
                name = name_node.text.decode('utf-8') if name_node else "[Anonymous]"
            elif node_type == 'namespace_definition':
                name_node = node.child_by_field_name('name')
                name = name_node.text.decode('utf-8') if name_node else "[Anonymous Namespace]"
            elif node_type in ['function_definition', 'declaration']: # Includes functions, methods, constructors, destructors, simple declarations
                declarator = node.child_by_field_name('declarator')
                if declarator:
                    name_node = self._find_name_in_declarator(declarator)
                    if name_node:
                         name = name_node.text.decode('utf-8')
                    else: # Try to find name differently if no typical declarator name found
                        if node_type == 'declaration' and node.child_by_field_name('type'): # e.g. simple variable declaration
                            potential_name = self.find_first_descendant(declarator, ['identifier'])
                            name = potential_name.text.decode('utf-8') if potential_name else "[Unnamed Declaration]"
                        else:
                            name = "[Unnamed Function/Declaration]"
                elif node_type == 'declaration' and not declarator: # e.g. `using namespace std;` parsed as declaration
                     using_declarator = self.find_first_descendant(node, ['namespace_identifier', 'qualified_identifier', 'identifier'])
                     name = using_declarator.text.decode('utf-8') if using_declarator else "[Using Declaration]"
                else:
                     name = "[Unnamed Function/Declaration]"

            elif node_type == 'field_declaration':
                declarator = node.child_by_field_name('declarator')
                if declarator:
                    name_node = self._find_name_in_declarator(declarator)
                    name = name_node.text.decode('utf-8') if name_node else "[Unnamed Field]"
                else: name = "[Unnamed Field]"
            # parameter_declaration name extraction is usually not needed at top level
            elif node_type == 'type_alias_declaration': # using Name = ...;
                 name_node = node.child_by_field_name('name') # This should be 'identifier' type
                 name = name_node.text.decode('utf-8') if name_node else "[Unnamed Type Alias]"
            elif node_type == 'using_declaration': # using namespace::identifier;
                 # The name is the full path being used
                 name_node = self.find_first_descendant(node, ['qualified_identifier', 'identifier'])
                 name = name_node.text.decode('utf-8') if name_node else "[Unnamed Using]"
            elif node_type == 'template_declaration':
                 content_node = node.child_by_field_name('declaration') or node.child_by_field_name('definition') # Adjust field names based on actual grammar
                 if not content_node: # Fallback if fields differ
                     content_node = node.named_child(node.named_child_count -1) # Assume last named child is content

                 if content_node:
                     try:
                         # Get name of the templated entity
                         base_name = self.get_entity_name(content_node)
                         # Extract template parameters for better representation if needed
                         params_node = node.child_by_field_name('parameters')
                         params_text = params_node.text.decode('utf-8') if params_node else ""
                         name = f"{base_name}{params_text}"
                     except ValueError:
                         name = "[Unnamed Template Content]"
                 else: name = "[Invalid Template]"

        except Exception as e:
            logger.error(f"Error getting name for node {node.type} ({node.start_byte}-{node.end_byte}): {e}\nNode S-exp: {node.sexp()}", exc_info=True)
            return "[Error Extracting Name]"

        return name


    def get_entity_docstring(self, node: Node) -> Optional[str]:
        # Код остается прежним из упрощенной версии
        previous_sibling = node.prev_named_sibling
        if previous_sibling and previous_sibling.type == 'comment':
            comment_text = previous_sibling.text.decode('utf-8')
            if comment_text.startswith('///') or comment_text.startswith('/**'):
                lines = comment_text.splitlines()
                cleaned_lines = []
                for line in lines:
                    l = line.strip()
                    if l.startswith('/**'): l = l[3:]
                    elif l.startswith('/*'): l = l[2:] # Handle standard block comments used as docstrings too?
                    elif l.startswith('*'): l = l[1:]
                    elif l.startswith('///'): l = l[3:]
                    if l.endswith('*/'): l = l[:-2]
                    cleaned_lines.append(l.strip())
                while cleaned_lines and not cleaned_lines[0]: cleaned_lines.pop(0)
                while cleaned_lines and not cleaned_lines[-1]: cleaned_lines.pop(-1)
                return "\n".join(cleaned_lines) if cleaned_lines else None
        return None


    def get_entity_types(self) -> List[str]:
        # Код остается прежним
        return [
            'class_specifier', 'struct_specifier', 'union_specifier', 'enum_specifier',
            'namespace_definition', 'function_definition',
            'declaration', # Filtered later in parsing to find functions, ctors, dtors etc.
            'field_declaration',
            'template_declaration',
            'type_alias_declaration',
            'using_declaration'
        ]

    def add_symbols(self, entity: Entity) -> None:
        # Код остается прежним из упрощенной версии
        node = entity.node
        node_type = node.type

        # 1. Inheritance
        if node_type in ['class_specifier', 'struct_specifier']:
            base_clause_query = self.language.query("""
                (base_clause (base_specifier type: $type)) @base_spec
                where $type = [
                    (type_identifier) @base_id
                    (qualified_identifier) @base_id
                    (template_type name: _ @base_id)
                ]
                """)
            for child in node.children:
                 if child.type == 'base_clause':
                     captures = base_clause_query.captures(child)
                     for cap_node, name in captures:
                         if name == 'base_id':
                             entity.add_symbol("base_class", cap_node)
                             break # Assume one type per base_specifier for simplicity now
                     break

        # 2. Function Calls
        body_node: Optional[Node] = None
        if node_type == 'function_definition':
            body_node = node.child_by_field_name('body')
        elif node_type == 'declaration': # Constructors/Destructors with body
             declarator = node.child_by_field_name('declarator')
             if declarator and declarator.type == 'function_declarator':
                 last_child = node.last_named_child
                 if last_child and last_child.type == 'compound_statement': # Check if body exists
                     body_node = last_child

        if body_node:
            call_query = self.language.query("""
                (call_expression
                  function: [
                    (identifier) @call_target
                    (qualified_identifier) @call_target
                    (field_expression field: [ (identifier) @call_target (qualified_identifier) @call_target ]) # a.foo() or a.ns::foo()
                    (pointer_expression field: [ (identifier) @call_target (qualified_identifier) @call_target ]) # a->foo() or a->ns::foo()
                    (template_function name: _ @call_target) # foo<T>() - captures name part
                     # Add more complex call patterns if needed (e.g., operators)
                  ]
                ) @call_expr
            """)
            captures = call_query.captures(body_node)
            unique_calls = {} # Use dict to store unique call targets (by node id)
            for cap_node, name in captures:
                 if name == 'call_target':
                     # Store the node representing the thing being called
                     if cap_node.id not in unique_calls:
                         entity.add_symbol("call", cap_node)
                         unique_calls[cap_node.id] = cap_node

        # 3. Types (Return, Parameters, Fields)
        type_query_str = """
            [
             (type_identifier) @type_id
             (qualified_identifier) @type_id
             (primitive_type) @type_id
             (template_type name: _ @type_id) # Captures the base name of the template type
             # Try to capture the underlying type for pointers/references
             (pointer_declarator type: @type_id)
             (reference_declarator type: @type_id)
             (parameter_declaration type: @type_id) # Recursive? Careful
             # Base types inside complex types
             (pointer_type declarator: (type_identifier) @type_id)
             (reference_type declarator: (type_identifier) @type_id)
             # etc. - This part might need refinement based on grammar details
            ]
        """
        type_query = self.language.query(type_query_str) # Define query once

        # Return Type
        if node_type == 'function_definition' or (node_type == 'declaration' and node.child_by_field_name('declarator') and node.child_by_field_name('declarator').type == 'function_declarator'):
            type_node = node.child_by_field_name('type')
            if type_node:
                 # Try to find the core type identifier(s) within the type node
                 captures = type_query.captures(type_node)
                 for cap_node, name in captures:
                     if name == 'type_id':
                         entity.add_symbol("return_type", cap_node)
                         break # Often only need the first core type found

            # Parameters
            declarator = node.child_by_field_name('declarator')
            if declarator and declarator.type == 'function_declarator':
                param_list = declarator.child_by_field_name('parameters')
                if param_list:
                     # Query for types inside parameter declarations
                     param_type_query = self.language.query(f"(parameter_declaration type: $type) @param where $type = {type_query_str}")
                     # Add optional_parameter_declaration, variadic etc if needed
                     captures = param_type_query.captures(param_list)
                     unique_param_types = {}
                     for cap_node, name in captures:
                          if name == 'type_id': # Node representing the type
                              if cap_node.id not in unique_param_types:
                                 entity.add_symbol("parameter_type", cap_node)
                                 unique_param_types[cap_node.id] = cap_node

        # Field Types
        elif node_type in ['class_specifier', 'struct_specifier']:
             body_node = node.child_by_field_name('body')
             if body_node and body_node.type == 'field_declaration_list':
                 # Query for types inside field declarations
                 field_type_query = self.language.query(f"(field_declaration type: $type) @field where $type = {type_query_str}")
                 captures = field_type_query.captures(body_node)
                 unique_field_types = {}
                 for cap_node, name in captures:
                     if name == 'type_id': # Node representing the type
                        if cap_node.id not in unique_field_types:
                             entity.add_symbol("field_type", cap_node)
                             unique_field_types[cap_node.id] = cap_node


    def resolve_path(self, file_path: str, path: Path) -> str:
        """(Simplified) Resolves a file path relative to the project root 'path'."""
        # Этот метод должен соответствовать сигнатуре AbstractAnalyzer
        p = Path(file_path)
        # Если путь уже абсолютный, возвращаем его как есть
        if p.is_absolute():
            return str(p)
        else:
            # Иначе делаем его абсолютным относительно path (корня проекта)
            # Используем сохраненный _project_root если он есть и path не передан явно (?)
            # Используем `path` как передано в сигнатуре
            abs_p = (path / p).resolve()
            logger.debug(f"Resolved relative path '{file_path}' to '{abs_p}' using base '{path}'")
            return str(abs_p)

    # --- Исправленная реализация resolve_symbol ---
    def resolve_symbol(self, files: Dict[Path, File], lsp: Optional, file_path: Path, path: Path, key: str, symbol_node: Node) -> Optional[Entity]:
        """
        (Simplified/Dummy) Attempts to resolve symbols based on name (unreliable).
        Returns None as accurate resolution without LSP is not feasible.
        Matches the AbstractAnalyzer signature, but ignores LSP.
        """
        symbol_text = symbol_node.text.decode('utf-8')
        logger.warning(f"Attempting simplified symbol resolution (name search - unreliable) for: key='{key}', symbol='{symbol_text}' in {file_path}. LSP is ignored.")

        # --- ПРОСТОЙ ПОИСК ПО ИМЕНИ (ОЧЕНЬ НЕНАДЕЖНО!) ---
        # Эта часть оставлена для примера, но она не будет работать корректно
        # для перегруженных функций, шаблонов, пространств имен и т.д.
        target_entity_types = []
        if key in ["base_class", "return_type", "parameter_type", "field_type"]:
             # Ищем классы, структуры, перечисления, псевдонимы типов
             target_entity_types = ['class_specifier', 'struct_specifier', 'enum_specifier', 'type_alias_declaration', 'union_specifier']
        elif key == "call":
             # Ищем функции, методы, конструкторы, деструкторы
             target_entity_types = ['function_definition', 'declaration'] # declaration может быть методом/конструктором/деструктором

        found_entities: List[Entity] = []
        if target_entity_types:
             # Ищем по всем файлам сущность с подходящим именем и типом
             for file_obj in files.values():
                for entity in file_obj.entities.values():
                    try:
                        # Сравниваем имя (может понадобиться обработка ::)
                        entity_name = self.get_entity_name(entity.node)
                        # Простое сравнение (не учитывает квалификаторы!)
                        if entity_name == symbol_text.split('::')[-1]: # Сравниваем последнюю часть имени
                            # Проверяем тип ноды сущности
                            if entity.node.type in target_entity_types:
                                # Дополнительная проверка для 'declaration', чтобы убедиться, что это функция/метод
                                if entity.node.type == 'declaration':
                                     declarator = entity.node.child_by_field_name('declarator')
                                     if not (declarator and declarator.type == 'function_declarator'):
                                         continue # Пропускаем не-функциональные декларации

                                logger.debug(f"Potential (unverified) match found for '{symbol_text}': {entity_name} in {file_obj.path}")
                                found_entities.append(entity)
                    except Exception as e:
                        logger.error(f"Error comparing entity during simple name search: {e}")
                        continue

        # --- ВОЗВРАТ РЕЗУЛЬТАТА ---
        # Поскольку надежное разрешение невозможно, возвращаем None.
        # Если простой поиск что-то нашел, можно вернуть первое совпадение,
        # но это ОЧЕНЬ ВЕРОЯТНО будет НЕПРАВИЛЬНО.
        if found_entities:
             logger.warning(f"Found {len(found_entities)} potential matches for '{symbol_text}' via basic name search. Returning None due to unreliability.")
             # Можно вернуть found_entities[0], если нужно хоть что-то, но с большим предупреждением.
             # return found_entities[0] # НЕ РЕКОМЕНДУЕТСЯ

        logger.warning(f"Reliable symbol resolution for key '{key}' ('{symbol_text}') requires LSP and compile commands. Returning None.")
        return None # Соответствует сигнатуре -> Optional[Entity] (если ее изменить) или выбрасывать ошибку/возвращать Dummy Entity


    # --- Вспомогательные методы ---
    # find_parent уже есть в AbstractAnalyzer, можно использовать super().find_parent(..) или скопировать реализацию, если нужно
    # def find_parent(self, node: Node, types: List[str]) -> Optional[Node]:
    #     """Traverses up the tree to find the first ancestor node matching one of the types."""
    #     # Можно использовать реализацию из базового класса:
    #     # return super().find_parent(node, types)
    #     # Или оставить кастомную:
    #     current = node.parent
    #     while current:
    #         if current.type in types:
    #             return current
    #         current = current.parent
    #     return None

    def find_first_descendant(self, node: Node, types: List[str]) -> Optional[Node]:
        """Helper to find the first descendant node matching one of the types (BFS)."""
        # Код остается прежним
        queue = list(node.children)
        visited = {node.id} | {child.id for child in queue}
        while queue:
            current_node = queue.pop(0)
            if current_node.type in types:
                return current_node
            for child in current_node.children:
                 if child.id not in visited:
                    queue.append(child)
                    visited.add(child.id)
        return None
