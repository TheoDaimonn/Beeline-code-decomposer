import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import os
import subprocess
from multilspy import SyncLanguageServer
from pathlib import Path

from ...entities import *
from typing import Optional
from ..analyzer import AbstractAnalyzer

from tree_sitter import Language, Node

import logging

from ..analyzer import AbstractAnalyzer
logger = logging.getLogger('code_graph')

import tree_sitter_cpp as tscpp
class CppAnalyzer(AbstractAnalyzer):
    def __init__(self) -> None:
        super().__init__(Language(tscpp.language()))

    def add_dependencies(self, path: Path, files: list[Path]):
        # C++ dependency handling is project-specific. Placeholder logic:
        build_dir = path / "build"
        if not build_dir.exists():
            build_dir.mkdir()
            subprocess.run(["cmake", "-S", ".", "-B", "build"], cwd=str(path))
            subprocess.run(["cmake", "--build", "build"], cwd=str(path))

        # Simulate collecting source files
        files.extend(path.rglob("*.h"))
        files.extend(path.rglob("*.cpp"))

    def get_entity_label(self, node: Node) -> str:
        if node.type == 'class_specifier':
            return "Class"
        elif node.type == 'function_definition':
            return "Function"
        raise ValueError(f"Unknown entity type: {node.type}")

    def get_entity_name(self, node: Node) -> str:
        if node.type == 'class_specifier':
            # Find the class name inside the class_specifier
            for child in node.children:
                if child.type == 'type_identifier':
                    return child.text.decode('utf-8')
        elif node.type == 'function_definition':
            declarator = node.child_by_field_name('declarator')
            if declarator:
                for child in declarator.children:
                    if child.type == 'identifier':
                        return child.text.decode('utf-8')
        raise ValueError(f"Unknown entity type: {node.type}")

    def get_entity_docstring(self, node: Node) -> Optional[str]:
        # In C++, docstrings are typically comments before the declaration
        if node.prev_sibling and node.prev_sibling.type == 'comment':
            return node.prev_sibling.text.decode('utf-8')
        return None

    def get_entity_types(self) -> List[str]:
        return ['class_specifier', 'function_definition']

    def add_symbols(self, entity: Entity) -> None:
        if entity.node.type == 'class_specifier':
            base_clause = entity.node.child_by_field_name("base_clause")
            if base_clause:
                base_query = self.language.query("(base_class_clause (scoped_identifier) @base_class)")
                captures = base_query.captures(base_clause)
                for base_class in captures.get("base_class", []):
                    entity.add_symbol("base_class", base_class)

        elif entity.node.type == 'function_definition':
            # Parameters
            declarator = entity.node.child_by_field_name("declarator")
            if declarator:
                param_list = declarator.child_by_field_name("parameters")
                if param_list:
                    param_query = self.language.query("(parameter_declaration type: (_) @type)")
                    captures = param_query.captures(param_list)
                    for param_type in captures.get("type", []):
                        entity.add_symbol("parameters", param_type)

            # Return type
            return_type = entity.node.child_by_field_name("type")
            if return_type:
                entity.add_symbol("return_type", return_type)

            # Calls
            body = entity.node.child_by_field_name("body")
            if body:
                call_query = self.language.query("(call_expression function: (_) @call)")
                captures = call_query.captures(body)
                for call in captures.get("call", []):
                    entity.add_symbol("call", call)

    def is_dependency(self, file_path: str) -> bool:
        return "build" in file_path or ".git" in file_path

    def resolve_path(self, file_path: str, path: Path) -> str:
        return file_path

    def resolve_type(self, files: Dict[Path, File], lsp: SyncLanguageServer, file_path: Path, path, node: Node) -> List[Entity]:
        res = []
        if node.type == 'field_expression':
            node = node.child_by_field_name('field')
        for file, resolved_node in self.resolve(files, lsp, file_path, path, node):
            type_dec = self.find_parent(resolved_node, ['class_specifier'])
            if type_dec in file.entities:
                res.append(file.entities[type_dec])
        return res

    def resolve_method(self, files: Dict[Path, File], lsp: SyncLanguageServer, file_path: Path, path: Path, node: Node) -> List[Entity]:
        res = []
        if node.type == 'call_expression':
            node = node.child_by_field_name('function')
            if node.type == 'field_expression':
                node = node.child_by_field_name('field')
        for file, resolved_node in self.resolve(files, lsp, file_path, path, node):
            method_dec = self.find_parent(resolved_node, ['function_definition', 'class_specifier'])
            if not method_dec:
                continue
            if method_dec in file.entities:
                res.append(file.entities[method_dec])
        return res

    def resolve_symbol(self, files: Dict[Path, File], lsp: SyncLanguageServer, file_path: Path, path: Path, key: str, symbol: Node) -> Entity:
        if key in ["base_class", "parameters", "return_type"]:
            return self.resolve_type(files, lsp, file_path, path, symbol)
        elif key in ["call"]:
            return self.resolve_method(files, lsp, file_path, path, symbol)
        else:
            raise ValueError(f"Unknown key {key}")