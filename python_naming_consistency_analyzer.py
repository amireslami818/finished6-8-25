#!/usr/bin/env python3
"""
Python Naming Consistency Analyzer & Bug Detector

A comprehensive tool for analyzing Python codebases to identify naming inconsistencies,
semantic mismatches, and potential bugs related to variable, function, and parameter naming.

Usage:
    python naming_consistency_analyzer.py [path_to_project]
    python naming_consistency_analyzer.py --help

Features:
- Identifies core vs auxiliary files
- Maps data flow between modules
- Extracts function signatures and variable usage
- Detects naming inconsistencies
- Generates detailed reports
- Suggests refactoring opportunities

Requirements:
    pip install ast, pathlib, json, argparse, collections, re
"""

import ast
import os
import sys
import json
import argparse
import re
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Any, Optional
from dataclasses import dataclass, field
import importlib.util


@dataclass
class FunctionSignature:
    """Represents a function signature with detailed metadata"""
    name: str
    parameters: List[str]
    return_annotation: Optional[str] = None
    docstring: Optional[str] = None
    module: str = ""
    line_number: int = 0
    is_method: bool = False
    class_name: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    
    
@dataclass
class VariableUsage:
    """Tracks variable usage patterns"""
    name: str
    context: str  # assignment, parameter, return, etc.
    scope: str    # function, class, module
    scope_name: str
    line_number: int
    module: str
    related_functions: List[str] = field(default_factory=list)


@dataclass
class NamingInconsistency:
    """Represents a detected naming inconsistency"""
    type: str  # parameter_variable_mismatch, function_naming_pattern, etc.
    severity: str  # high, medium, low
    description: str
    locations: List[Tuple[str, int]]  # (file, line_number)
    suggestion: str
    related_items: List[str] = field(default_factory=list)


class PythonProjectAnalyzer:
    """Main analyzer class for Python project naming consistency"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.core_files: List[Path] = []
        self.auxiliary_files: List[Path] = []
        self.function_signatures: Dict[str, List[FunctionSignature]] = defaultdict(list)
        self.variable_usage: Dict[str, List[VariableUsage]] = defaultdict(list)
        self.naming_inconsistencies: List[NamingInconsistency] = []
        self.module_dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.data_flow_map: Dict[str, Dict[str, Any]] = {}
        
    def analyze_project(self) -> Dict[str, Any]:
        """Main analysis method - orchestrates the entire process"""
        print("🔍 Starting Python Project Naming Consistency Analysis...")
        
        # Step 1: Identify and classify files
        self._identify_files()
        
        # Step 2: Analyze each Python file
        self._analyze_python_files()
        
        # Step 3: Map data flow and dependencies
        self._map_data_flow()
        
        # Step 4: Detect naming inconsistencies
        self._detect_naming_inconsistencies()
        
        # Step 5: Generate comprehensive report
        return self._generate_report()
    
    def _identify_files(self):
        """Step 1: Identify core vs auxiliary files"""
        print("📁 Identifying and classifying project files...")
        
        python_files = list(self.project_path.rglob("*.py"))
        
        # Core file indicators
        core_indicators = [
            "main", "app", "server", "client", "api", "core", "engine",
            "pipeline", "workflow", "process", "step", "stage"
        ]
        
        # Auxiliary file indicators  
        aux_indicators = [
            "test", "spec", "config", "settings", "util", "helper", 
            "tool", "script", "setup", "__init__", "constants"
        ]
        
        for py_file in python_files:
            file_stem = py_file.stem.lower()
            file_content = self._get_file_content(py_file)
            
            # Skip empty files
            if not file_content or len(file_content.strip()) < 50:
                continue
                
            # Classify based on name patterns and content
            is_core = any(indicator in file_stem for indicator in core_indicators)
            is_aux = any(indicator in file_stem for indicator in aux_indicators)
            
            # Content-based classification
            if not is_core and not is_aux:
                is_core = self._analyze_file_importance(py_file, file_content)
            
            if is_core:
                self.core_files.append(py_file)
            else:
                self.auxiliary_files.append(py_file)
        
        print(f"   ✅ Core files identified: {len(self.core_files)}")
        print(f"   ✅ Auxiliary files identified: {len(self.auxiliary_files)}")
    
    def _analyze_file_importance(self, file_path: Path, content: str) -> bool:
        """Determine if a file is core based on content analysis"""
        try:
            tree = ast.parse(content)
            
            # Count significant elements
            function_count = len([node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)])
            class_count = len([node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)])
            import_count = len([node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))])
            
            # Core indicators: complex files with multiple functions/classes
            complexity_score = function_count * 2 + class_count * 3 + import_count
            
            return complexity_score > 15  # Threshold for core file classification
            
        except SyntaxError:
            return False
    
    def _analyze_python_files(self):
        """Step 2: Extract detailed information from each Python file"""
        print("🔬 Analyzing Python files for functions, variables, and patterns...")
        
        all_files = self.core_files + self.auxiliary_files
        
        for py_file in all_files:
            try:
                content = self._get_file_content(py_file)
                if not content:
                    continue
                    
                tree = ast.parse(content)
                module_name = self._get_module_name(py_file)
                
                # Extract function signatures
                self._extract_function_signatures(tree, module_name, py_file)
                
                # Extract variable usage patterns
                self._extract_variable_usage(tree, module_name, py_file)
                
                # Extract module dependencies
                self._extract_dependencies(tree, module_name)
                
            except SyntaxError as e:
                print(f"   ⚠️ Syntax error in {py_file}: {e}")
            except Exception as e:
                print(f"   ⚠️ Error analyzing {py_file}: {e}")
        
        print(f"   ✅ Extracted {sum(len(sigs) for sigs in self.function_signatures.values())} function signatures")
        print(f"   ✅ Tracked {sum(len(vars) for vars in self.variable_usage.values())} variable usages")
    
    def _extract_function_signatures(self, tree: ast.AST, module_name: str, file_path: Path):
        """Extract detailed function signature information"""
        
        class FunctionVisitor(ast.NodeVisitor):
            def __init__(self, analyzer):
                self.analyzer = analyzer
                self.current_class = None
                
            def visit_ClassDef(self, node):
                old_class = self.current_class
                self.current_class = node.name
                self.generic_visit(node)
                self.current_class = old_class
                
            def visit_FunctionDef(self, node):
                # Extract parameters
                params = []
                for arg in node.args.args:
                    params.append(arg.arg)
                
                # Extract decorators
                decorators = []
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name):
                        decorators.append(decorator.id)
                    elif isinstance(decorator, ast.Attribute):
                        decorators.append(f"{decorator.attr}")
                
                # Extract docstring
                docstring = None
                if (node.body and isinstance(node.body[0], ast.Expr) and 
                    isinstance(node.body[0].value, ast.Constant) and 
                    isinstance(node.body[0].value.value, str)):
                    docstring = node.body[0].value.value
                
                # Create function signature
                signature = FunctionSignature(
                    name=node.name,
                    parameters=params,
                    return_annotation=ast.unparse(node.returns) if node.returns else None,
                    docstring=docstring,
                    module=module_name,
                    line_number=node.lineno,
                    is_method=self.current_class is not None,
                    class_name=self.current_class,
                    decorators=decorators
                )
                
                self.analyzer.function_signatures[module_name].append(signature)
                self.generic_visit(node)
        
        visitor = FunctionVisitor(self)
        visitor.visit(tree)
    
    def _extract_variable_usage(self, tree: ast.AST, module_name: str, file_path: Path):
        """Extract variable usage patterns and contexts"""
        
        class VariableVisitor(ast.NodeVisitor):
            def __init__(self, analyzer):
                self.analyzer = analyzer
                self.current_function = None
                self.current_class = None
                
            def visit_ClassDef(self, node):
                old_class = self.current_class
                self.current_class = node.name
                self.generic_visit(node)
                self.current_class = old_class
                
            def visit_FunctionDef(self, node):
                old_function = self.current_function
                self.current_function = node.name
                
                # Track parameter usage
                for arg in node.args.args:
                    usage = VariableUsage(
                        name=arg.arg,
                        context="parameter",
                        scope="function",
                        scope_name=node.name,
                        line_number=node.lineno,
                        module=module_name
                    )
                    self.analyzer.variable_usage[arg.arg].append(usage)
                
                self.generic_visit(node)
                self.current_function = old_function
                
            def visit_Assign(self, node):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        scope = "function" if self.current_function else "module"
                        scope_name = self.current_function or module_name
                        
                        usage = VariableUsage(
                            name=target.id,
                            context="assignment",
                            scope=scope,
                            scope_name=scope_name,
                            line_number=node.lineno,
                            module=module_name
                        )
                        self.analyzer.variable_usage[target.id].append(usage)
                
                self.generic_visit(node)
        
        visitor = VariableVisitor(self)
        visitor.visit(tree)
    
    def _extract_dependencies(self, tree: ast.AST, module_name: str):
        """Extract module dependencies and imports"""
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.module_dependencies[module_name].add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.module_dependencies[module_name].add(node.module)
    
    def _map_data_flow(self):
        """Step 3: Map data flow between modules and functions"""
        print("🔄 Mapping data flow and inter-module relationships...")
        
        # Analyze function call patterns
        for module_name, signatures in self.function_signatures.items():
            module_flow = {
                "functions": [sig.name for sig in signatures],
                "dependencies": list(self.module_dependencies[module_name]),
                "complexity_score": len(signatures),
                "key_functions": self._identify_key_functions(signatures)
            }
            self.data_flow_map[module_name] = module_flow
        
        print(f"   ✅ Mapped data flow for {len(self.data_flow_map)} modules")
    
    def _identify_key_functions(self, signatures: List[FunctionSignature]) -> List[str]:
        """Identify key functions based on naming patterns and complexity"""
        key_patterns = [
            r"^main$", r"^run_", r"^execute_", r"^process_", r"^handle_",
            r"^save_", r"^load_", r"^fetch_", r"^create_", r"^update_"
        ]
        
        key_functions = []
        for sig in signatures:
            if any(re.match(pattern, sig.name) for pattern in key_patterns):
                key_functions.append(sig.name)
            elif len(sig.parameters) > 3:  # Complex functions
                key_functions.append(sig.name)
        
        return key_functions
    
    def _detect_naming_inconsistencies(self):
        """Step 4: Detect various types of naming inconsistencies"""
        print("🔍 Detecting naming inconsistencies and potential bugs...")
        
        # Detect parameter vs variable mismatches
        self._detect_parameter_variable_mismatches()
        
        # Detect function naming pattern inconsistencies
        self._detect_function_naming_patterns()
        
        # Detect variable naming inconsistencies
        self._detect_variable_naming_patterns()
        
        # Detect semantic mismatches
        self._detect_semantic_mismatches()
        
        # Detect cross-module inconsistencies
        self._detect_cross_module_inconsistencies()
        
        print(f"   ✅ Detected {len(self.naming_inconsistencies)} potential issues")
    
    def _detect_parameter_variable_mismatches(self):
        """Detect cases where parameter names don't match related variable names"""
        
        for module_name, signatures in self.function_signatures.items():
            for sig in signatures:
                # Look for variables in the same function scope
                function_variables = [
                    var for var in self.variable_usage.values() 
                    for usage in var 
                    if usage.scope_name == sig.name and usage.context == "assignment"
                ]
                
                # Check for semantic similarity but lexical difference
                for param in sig.parameters:
                    similar_vars = self._find_semantically_similar_names(
                        param, [usage.name for var in function_variables for usage in var]
                    )
                    
                    if similar_vars:
                        inconsistency = NamingInconsistency(
                            type="parameter_variable_mismatch",
                            severity="medium",
                            description=f"Parameter '{param}' in function '{sig.name}' has similar variables: {similar_vars}",
                            locations=[(sig.module, sig.line_number)],
                            suggestion=f"Consider renaming to maintain consistency",
                            related_items=[param] + similar_vars
                        )
                        self.naming_inconsistencies.append(inconsistency)
    
    def _detect_function_naming_patterns(self):
        """Detect inconsistent function naming patterns"""
        
        # Group functions by similar patterns
        pattern_groups = defaultdict(list)
        
        for module_name, signatures in self.function_signatures.items():
            for sig in signatures:
                # Extract naming patterns (prefixes, suffixes, etc.)
                patterns = self._extract_naming_patterns(sig.name)
                for pattern in patterns:
                    pattern_groups[pattern].append((sig, module_name))
        
        # Look for inconsistencies within pattern groups
        for pattern, functions in pattern_groups.items():
            if len(functions) > 1:
                names = [func[0].name for func in functions]
                if self._has_naming_inconsistency(names):
                    inconsistency = NamingInconsistency(
                        type="function_naming_pattern",
                        severity="low",
                        description=f"Functions with pattern '{pattern}' have inconsistent naming: {names}",
                        locations=[(func[1], func[0].line_number) for func in functions],
                        suggestion="Standardize naming pattern across similar functions",
                        related_items=names
                    )
                    self.naming_inconsistencies.append(inconsistency)
    
    def _detect_variable_naming_patterns(self):
        """Detect inconsistent variable naming patterns"""
        
        # Look for variables with similar semantic meaning but different names
        semantic_groups = defaultdict(list)
        
        for var_name, usages in self.variable_usage.items():
            semantic_key = self._get_semantic_key(var_name)
            semantic_groups[semantic_key].extend([(var_name, usage) for usage in usages])
        
        for semantic_key, var_usages in semantic_groups.items():
            if len(set(var[0] for var in var_usages)) > 1:  # Multiple variable names for same semantic
                var_names = list(set(var[0] for var in var_usages))
                if len(var_names) > 1 and self._are_semantically_similar(var_names):
                    inconsistency = NamingInconsistency(
                        type="variable_naming_pattern",
                        severity="medium",
                        description=f"Variables with similar semantics have different names: {var_names}",
                        locations=[(usage[1].module, usage[1].line_number) for usage in var_usages[:3]],
                        suggestion="Use consistent naming for semantically similar variables",
                        related_items=var_names
                    )
                    self.naming_inconsistencies.append(inconsistency)
    
    def _detect_semantic_mismatches(self):
        """Detect semantic mismatches like footer vs summary"""
        
        # Define semantic synonym groups
        synonym_groups = [
            ["footer", "summary", "conclusion", "ending"],
            ["start", "begin", "init", "initialize"],
            ["process", "handle", "execute", "run"],
            ["data", "info", "information", "content"],
            ["config", "configuration", "settings", "options"],
            ["result", "output", "response", "answer"]
        ]
        
        for group in synonym_groups:
            # Find variables/functions using different synonyms
            found_names = defaultdict(list)
            
            for module_name, signatures in self.function_signatures.items():
                for sig in signatures:
                    for synonym in group:
                        if synonym in sig.name.lower():
                            found_names[synonym].append((sig.name, module_name, sig.line_number, "function"))
            
            for var_name, usages in self.variable_usage.items():
                for synonym in group:
                    if synonym in var_name.lower():
                        for usage in usages:
                            found_names[synonym].append((var_name, usage.module, usage.line_number, "variable"))
            
            # If multiple synonyms are used, flag as inconsistency
            if len(found_names) > 1:
                all_items = []
                locations = []
                for synonym, items in found_names.items():
                    all_items.extend([item[0] for item in items])
                    locations.extend([(item[1], item[2]) for item in items[:2]])
                
                inconsistency = NamingInconsistency(
                    type="semantic_mismatch",
                    severity="high",
                    description=f"Semantic synonyms used inconsistently: {list(found_names.keys())}",
                    locations=locations,
                    suggestion=f"Choose one term from {group} and use consistently",
                    related_items=all_items
                )
                self.naming_inconsistencies.append(inconsistency)
    
    def _detect_cross_module_inconsistencies(self):
        """Detect naming inconsistencies across modules"""
        
        # Find similar functions across modules
        all_functions = []
        for module_name, signatures in self.function_signatures.items():
            for sig in signatures:
                all_functions.append((sig.name, module_name, sig.line_number))
        
        # Group by semantic similarity
        for i, (name1, mod1, line1) in enumerate(all_functions):
            for name2, mod2, line2 in all_functions[i+1:]:
                if mod1 != mod2 and self._are_semantically_similar([name1, name2]):
                    if name1 != name2:  # Different names for similar functions
                        inconsistency = NamingInconsistency(
                            type="cross_module_inconsistency",
                            severity="medium",
                            description=f"Similar functions have different names across modules: '{name1}' vs '{name2}'",
                            locations=[(mod1, line1), (mod2, line2)],
                            suggestion="Consider standardizing function names across modules",
                            related_items=[name1, name2]
                        )
                        self.naming_inconsistencies.append(inconsistency)
    
    def _find_semantically_similar_names(self, name: str, candidates: List[str]) -> List[str]:
        """Find semantically similar names using various heuristics"""
        similar = []
        
        for candidate in candidates:
            if self._are_semantically_similar([name, candidate]) and name != candidate:
                similar.append(candidate)
        
        return similar
    
    def _are_semantically_similar(self, names: List[str]) -> bool:
        """Check if names are semantically similar"""
        if len(names) < 2:
            return False
        
        # Check for common roots, prefixes, suffixes
        for i, name1 in enumerate(names):
            for name2 in names[i+1:]:
                # Levenshtein distance check
                if self._levenshtein_distance(name1.lower(), name2.lower()) <= max(2, min(len(name1), len(name2)) // 3):
                    return True
                
                # Common substring check
                if len(self._longest_common_substring(name1.lower(), name2.lower())) >= min(len(name1), len(name2)) // 2:
                    return True
        
        return False
    
    def _extract_naming_patterns(self, name: str) -> List[str]:
        """Extract naming patterns from a function/variable name"""
        patterns = []
        
        # Split by underscores and camelCase
        parts = re.findall(r'[A-Z][a-z]*|[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', name)
        
        if len(parts) > 1:
            patterns.append(f"prefix_{parts[0].lower()}")
            patterns.append(f"suffix_{parts[-1].lower()}")
            if len(parts) > 2:
                patterns.append(f"middle_{parts[1].lower()}")
        
        return patterns
    
    def _get_semantic_key(self, name: str) -> str:
        """Get semantic key for grouping similar variables"""
        # Remove common prefixes/suffixes and convert to lowercase
        cleaned = re.sub(r'^(get_|set_|is_|has_)', '', name.lower())
        cleaned = re.sub(r'(_list|_dict|_data|_info)$', '', cleaned)
        return cleaned
    
    def _has_naming_inconsistency(self, names: List[str]) -> bool:
        """Check if a list of names has inconsistent patterns"""
        if len(names) < 2:
            return False
        
        # Check for mixed naming conventions (camelCase vs snake_case)
        has_camel = any('_' not in name and any(c.isupper() for c in name[1:]) for name in names)
        has_snake = any('_' in name for name in names)
        
        return has_camel and has_snake
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _longest_common_substring(self, s1: str, s2: str) -> str:
        """Find longest common substring between two strings"""
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        longest = 0
        ending_pos_i = 0
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                    if dp[i][j] > longest:
                        longest = dp[i][j]
                        ending_pos_i = i
                else:
                    dp[i][j] = 0
        
        return s1[ending_pos_i - longest: ending_pos_i]
    
    def _generate_report(self) -> Dict[str, Any]:
        """Step 5: Generate comprehensive analysis report"""
        print("📊 Generating comprehensive analysis report...")
        
        # Calculate statistics
        total_functions = sum(len(sigs) for sigs in self.function_signatures.values())
        total_variables = sum(len(vars) for vars in self.variable_usage.values())
        
        # Categorize inconsistencies by severity
        severity_counts = Counter(inc.severity for inc in self.naming_inconsistencies)
        type_counts = Counter(inc.type for inc in self.naming_inconsistencies)
        
        # Generate recommendations
        recommendations = self._generate_recommendations()
        
        report = {
            "project_path": str(self.project_path),
            "analysis_summary": {
                "total_files_analyzed": len(self.core_files) + len(self.auxiliary_files),
                "core_files": len(self.core_files),
                "auxiliary_files": len(self.auxiliary_files),
                "total_functions": total_functions,
                "total_variables": total_variables,
                "total_inconsistencies": len(self.naming_inconsistencies)
            },
            "file_classification": {
                "core_files": [str(f.relative_to(self.project_path)) for f in self.core_files],
                "auxiliary_files": [str(f.relative_to(self.project_path)) for f in self.auxiliary_files]
            },
            "data_flow_map": self.data_flow_map,
            "inconsistency_analysis": {
                "by_severity": dict(severity_counts),
                "by_type": dict(type_counts),
                "details": [
                    {
                        "type": inc.type,
                        "severity": inc.severity,
                        "description": inc.description,
                        "locations": inc.locations,
                        "suggestion": inc.suggestion,
                        "related_items": inc.related_items
                    }
                    for inc in self.naming_inconsistencies
                ]
            },
            "recommendations": recommendations,
            "function_signatures": {
                module: [
                    {
                        "name": sig.name,
                        "parameters": sig.parameters,
                        "return_annotation": sig.return_annotation,
                        "is_method": sig.is_method,
                        "class_name": sig.class_name,
                        "line_number": sig.line_number
                    }
                    for sig in signatures
                ]
                for module, signatures in self.function_signatures.items()
            }
        }
        
        return report
    
    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        # High severity issues first
        high_severity = [inc for inc in self.naming_inconsistencies if inc.severity == "high"]
        if high_severity:
            recommendations.append({
                "priority": "HIGH",
                "category": "Semantic Consistency",
                "action": "Address semantic mismatches immediately",
                "description": f"Found {len(high_severity)} high-severity naming issues that may cause bugs",
                "examples": [inc.description for inc in high_severity[:3]]
            })
        
        # Cross-module inconsistencies
        cross_module = [inc for inc in self.naming_inconsistencies if inc.type == "cross_module_inconsistency"]
        if cross_module:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Cross-Module Consistency",
                "action": "Standardize naming across modules",
                "description": f"Found {len(cross_module)} cross-module naming inconsistencies",
                "examples": [inc.description for inc in cross_module[:3]]
            })
        
        # Function naming patterns
        pattern_issues = [inc for inc in self.naming_inconsistencies if inc.type == "function_naming_pattern"]
        if pattern_issues:
            recommendations.append({
                "priority": "LOW",
                "category": "Naming Conventions",
                "action": "Establish consistent function naming patterns",
                "description": f"Found {len(pattern_issues)} function naming pattern issues",
                "examples": [inc.description for inc in pattern_issues[:3]]
            })
        
        return recommendations
    
    def _get_file_content(self, file_path: Path) -> Optional[str]:
        """Safely read file content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None
    
    def _get_module_name(self, file_path: Path) -> str:
        """Get module name from file path"""
        relative_path = file_path.relative_to(self.project_path)
        return str(relative_path.with_suffix(''))


def main():
    """Main entry point for the naming consistency analyzer"""
    parser = argparse.ArgumentParser(
        description="Python Naming Consistency Analyzer & Bug Detector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python naming_consistency_analyzer.py .
    python naming_consistency_analyzer.py /path/to/project
    python naming_consistency_analyzer.py . --output report.json
    python naming_consistency_analyzer.py . --verbose
        """
    )
    
    parser.add_argument(
        'project_path',
        nargs='?',
        default='.',
        help='Path to the Python project to analyze (default: current directory)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output file for the analysis report (JSON format)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--severity-filter',
        choices=['high', 'medium', 'low'],
        help='Filter inconsistencies by severity level'
    )
    
    args = parser.parse_args()
    
    # Validate project path
    project_path = Path(args.project_path).resolve()
    if not project_path.exists():
        print(f"❌ Error: Project path '{project_path}' does not exist")
        sys.exit(1)
    
    if not project_path.is_dir():
        print(f"❌ Error: Project path '{project_path}' is not a directory")
        sys.exit(1)
    
    # Run analysis
    print(f"🚀 Analyzing Python project: {project_path}")
    print("=" * 60)
    
    analyzer = PythonProjectAnalyzer(str(project_path))
    report = analyzer.analyze_project()
    
    # Filter by severity if requested
    if args.severity_filter:
        report['inconsistency_analysis']['details'] = [
            detail for detail in report['inconsistency_analysis']['details']
            if detail['severity'] == args.severity_filter
        ]
    
    # Output results
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"📄 Report saved to: {args.output}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 ANALYSIS SUMMARY")
    print("=" * 60)
    
    summary = report['analysis_summary']
    print(f"Files analyzed: {summary['total_files_analyzed']}")
    print(f"  - Core files: {summary['core_files']}")
    print(f"  - Auxiliary files: {summary['auxiliary_files']}")
    print(f"Functions analyzed: {summary['total_functions']}")
    print(f"Variables tracked: {summary['total_variables']}")
    print(f"Inconsistencies found: {summary['total_inconsistencies']}")
    
    if report['inconsistency_analysis']['by_severity']:
        print("\nBy severity:")
        for severity, count in report['inconsistency_analysis']['by_severity'].items():
            print(f"  - {severity.upper()}: {count}")
    
    if report['inconsistency_analysis']['by_type']:
        print("\nBy type:")
        for issue_type, count in report['inconsistency_analysis']['by_type'].items():
            print(f"  - {issue_type.replace('_', ' ').title()}: {count}")
    
    # Print recommendations
    if report['recommendations']:
        print("\n" + "=" * 60)
        print("💡 RECOMMENDATIONS")
        print("=" * 60)
        
        for rec in report['recommendations']:
            print(f"\n[{rec['priority']}] {rec['category']}")
            print(f"Action: {rec['action']}")
            print(f"Description: {rec['description']}")
            if rec.get('examples'):
                print("Examples:")
                for example in rec['examples']:
                    print(f"  - {example}")
    
    # Print top issues if verbose
    if args.verbose and report['inconsistency_analysis']['details']:
        print("\n" + "=" * 60)
        print("🔍 TOP ISSUES FOUND")
        print("=" * 60)
        
        for i, detail in enumerate(report['inconsistency_analysis']['details'][:5], 1):
            print(f"\n{i}. [{detail['severity'].upper()}] {detail['type'].replace('_', ' ').title()}")
            print(f"   Description: {detail['description']}")
            print(f"   Suggestion: {detail['suggestion']}")
            if detail['locations']:
                locations_str = ", ".join([f"{loc[0]}:{loc[1]}" for loc in detail['locations'][:3]])
                print(f"   Locations: {locations_str}")
    
    print(f"\n✅ Analysis complete! Found {summary['total_inconsistencies']} potential issues.")
    
    # Exit with appropriate code
    if summary['total_inconsistencies'] > 0:
        if any(detail['severity'] == 'high' for detail in report['inconsistency_analysis']['details']):
            sys.exit(2)  # High severity issues
        else:
            sys.exit(1)  # Medium/low severity issues
    else:
        sys.exit(0)  # No issues found


if __name__ == "__main__":
    main()
