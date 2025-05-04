import os
from pathlib import Path

from multilspy import SyncLanguageServer
from ...entities import *
from ...graph import Graph
from typing import Optional, List, Tuple
from ..analyzer import AbstractAnalyzer

from tree_sitter import Language, Node

# Load C++ grammar (ensure build/my-languages.so includes tree-sitter-cpp)
CPP_LANGUAGE = Language('build/my-languages.so', 'cpp')

import logging
logger = logging.getLogger('code_graph')

class CppAnalyzer(AbstractAnalyzer):
    def __init__(self) -> None:
        super().__init__(CPP_LANGUAGE)

    def get_entity_label(self, node: Node) -> str:
        if node.type in ('class_specifier', 'struct_specifier'):  # C++ classes/structs
            return 'Class'
        elif node.type == 'function_definition':
            return 'Function'
        raise ValueError(f"Unknown entity type: {node.type}")

    def get_entity_name(self, node: Node) -> str:
        if node.type in ('class_specifier', 'struct_specifier'):
            name_node = node.child_by_field_name('name')
        elif node.type == 'function_definition':
            decl = node.child_by_field_name('declarator')
            name_node = decl.child_by_field_name('declarator')
        else:
            raise ValueError(f"Unknown entity type: {node.type}")
        return name_node.text.decode('utf-8')

    def get_entity_docstring(self, node: Node) -> Optional[str]:
        # C++ comments not in AST; skip or use external comment extractor
        return None

    def get_entity_types(self) -> List[str]:
        return ['class_specifier', 'struct_specifier', 'function_definition']

    def process_parameter_declaration(self, node: Node) -> Tuple[bool, str, Optional[str]]:
        # Extract const, type (including references), and name
        const = False
        ref = False
        arg_type = ''
        arg_name = ''
        for child in node.children:
            if child.type == 'type_qualifier' and child.text == b'const':
                const = True
            elif child.type in ('primitive_type', 'scoped_identifier', 'type_identifier'):
                arg_type += child.text.decode('utf-8') + ' '
            elif child.type == 'reference_declarator':
                ref = True
            elif child.type == 'pointer_declarator':
                arg_type += '*'
            elif child.type == 'identifier':
                arg_name = child.text.decode('utf-8')
        type_str = ('const ' if const else '') + arg_type.strip() + ('&' if ref else '')
        return const, type_str, arg_name or None

    def process_function_definition_node(self, node: Node, path: Path,
                                         source_code: str) -> Optional[Function]:
        # Name
        decl = node.child_by_field_name('declarator')
        if not decl:
            return None
        name_node = decl.child_by_field_name('declarator')
        name = name_node.text.decode('utf-8')
        logger.info(f"Function: {name}")
        # Return type
        ret_node = node.child_by_field_name('type')
        ret_type = ret_node.text.decode('utf-8') if ret_node else 'void'
        # Parameters
        args = []
        param_list = decl.child_by_field_name('parameters')
        if param_list:
            for p in param_list.children:
                if p.type == 'parameter_declaration':
                    args.append(self.process_parameter_declaration(p))
        # Lines
        start_line = node.start_point[0]
        end_line = node.end_point[0]
        src = source_code[node.start_byte:node.end_byte]
        f = Function(str(path), name, '', ret_type, src, start_line, end_line)
        for const, t, n in args:
            if t == 'void' and n is None:
                continue
            f.add_argument(n, t)
        return f

    def process_function_definition(self, parent: File, node: Node, path: Path,
                                    graph: Graph, source_code: str) -> None:
        entity = self.process_function_definition_node(node, path, source_code)
        if not entity:
            return
        graph.add_function(entity)
        graph.connect_entities('DEFINES', parent.id, entity.id)

    def process_class_specifier(self, parent: File, node: Node, path: Path,
                                graph: Graph) -> None:
        assert node.type in ('class_specifier', 'struct_specifier')
        name_node = node.child_by_field_name('name')
        if not name_node:
            return
        name = name_node.text.decode('utf-8')
        start_line, end_line = node.start_point[0], node.end_point[0]
        c = Class(str(path), name, '', start_line, end_line)
        # Fields and methods
        body = node.child_by_field_name('body')
        if body:
            for child in body.children:
                if child.type == 'field_declaration':
                    # extract member vars
                    pass
                elif child.type == 'function_definition':
                    # process inline method
                    self.process_function_definition(c, child, path, graph, path.read_text().encode())
        graph.add_struct(c)
        graph.connect_entities('DEFINES', parent.id, c.id)

    def process_struct_specifier(self, parent: File, node: Node, path: Path,
                                 graph: Graph) -> None:
        # struct specifier same as class
        self.process_class_specifier(parent, node, path, graph)

    def second_pass(self, path: Path, graph: Graph) -> None:
        if path.suffix not in ('.cpp', '.hpp', '.h', '.cc', '.cxx'):
            logger.debug(f"Skip non-C++ file: {path}")
            return
        file = graph.get_file(os.path.dirname(path), path.name, path.suffix)
        if not file:
            return
        content = path.read_bytes()
        tree = self.parser.parse(content)
        # Function definitions
        q_fn = self.language.query("(function_definition declarator: (function_declarator) @fn)")
        for node, _ in q_fn.captures(tree.root_node):
            self.process_function_definition(file, node, path, graph, content.decode('utf-8'))
        # Calls
        q_call = self.language.query("(call_expression function: (identifier) @callee)")
        calls = q_call.captures(tree.root_node)
        for callee_node, _ in calls:
            caller = self.find_parent(callee_node, ['function_definition'])
            if not caller:
                continue
            caller_name = caller.child_by_field_name('declarator').text.decode('utf-8')
            callee_name = callee_node.text.decode('utf-8')
            caller_f = graph.get_function_by_name(caller_name)
            callee_f = graph.get_function_by_name(callee_name)
            if not callee_f:
                callee_f = Function('/', callee_name, None, None, None, 0, 0)
                graph.add_function(callee_f)
            graph.connect_entities('CALLS', caller_f.id, callee_f.id)

    def resolve_symbol(self, files: dict[Path, File], lsp: SyncLanguageServer,
                       path: Path, key: str, symbol: Node) -> Entity:
        if key in ('parameters', 'return_type'):
            return self.resolve_type(files, lsp, path, symbol)
        elif key == 'call':
            return self.resolve_method(files, lsp, path, symbol)
        else:
            raise ValueError(f"Unknown symbol key: {key}")

    def resolve_type(self, files, lsp, path, node):
        # similar to C logic
        return super().resolve_type(files, lsp, path, node)

    def resolve_method(self, files, lsp, path, node):
        return super().resolve_method(files, lsp, path, node)