from collections import defaultdict
import os
import ast


def extract_implementation(directory_path: str):
    """
    Given a directory path, extract the implementation of each type from source code files.
    """
    type_impls = defaultdict(
        list
    )  # Dictionary to hold the implementations of each type

    # Iterate over all files in the directory
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)

        # Only consider Python source code files
        if os.path.isfile(file_path) and filename.endswith(".py"):
            with open(file_path) as f:
                # Parse the AST for the file
                tree = ast.parse(f.read())

                # Find all class definitions in the AST
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        type_name = node.name

                        # Extract the implementation of the type
                        start_lineno, _ = node.lineno, node.col_offset
                        end_lineno = node.body[-1].end_lineno
                        with open(file_path) as f:
                            lines = f.readlines()[start_lineno - 1 : end_lineno]
                        type_impl = "".join(lines)

                        # Add the implementation to the dictionary
                        type_impls[type_name].append(type_impl)

    return type_impls
