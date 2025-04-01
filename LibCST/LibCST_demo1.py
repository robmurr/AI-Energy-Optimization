import libcst as cst

def mock_ml_model(node: cst.CSTNode):
    if isinstance(node, cst.BinaryOperation) and isinstance(node.operator, cst.Power):
        return f"math.pow({cst.Module([]).code_for_node(node.left)}, {cst.Module([]).code_for_node(node.right)})"
    return None

#sub-class of CSTTransformer class
class MLTransformer(cst.CSTTransformer):
    def __init__(self):
        self.should_add_math_import = False

#overwritten some method in cst transformer
    def leave_BinaryOperation(self, original_node: cst.BinaryOperation,updated_node: cst.BinaryOperation):
        replacement_code = mock_ml_model(original_node)

        if replacement_code:
            self.should_add_math_import = True
            return cst.parse_expression(replacement_code)
        return updated_node

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        if self.should_add_math_import:
            import_math = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("math"))])])
            return updated_node.with_changes(body=[import_math] + list(updated_node.body))
        return updated_node


def optimize_code(input_code):
    # Parse code to CST
    module = cst.parse_module(input_code)

    # Apply transformations
    transformer = MLTransformer()
    transformed_module = module.visit(transformer)

    # Generate final code
    return transformed_module.code


if __name__ == "__main__":
    original_code = """
#testing code
def calculate(a, b):
    c = a**b
    return c
    """

    print("Original Code:")
    print(original_code)

    print("\nOptimized Code:")
    optimized_code = optimize_code(original_code)
    print(optimized_code)
