"""Canonical argument packing for experimental typed variadic functions.

This helper is deliberately not wired into QRVM calls until semantic validation
and the runtime container representation have been reviewed together.
"""


def pack_variadic_arguments(parameters, arguments, variadic_index=None):
    """Return a local-name mapping, grouping trailing values in a tuple.

    Fixed-arity calls preserve the existing behavior. The tuple is a temporary
    immutable carrier; the language-level collection type is not yet decided.
    """
    if len(set(parameters)) != len(parameters):
        raise ValueError("Duplicate parameter names")
    if variadic_index is None:
        if len(parameters) != len(arguments):
            raise ValueError("Fixed-arity argument count mismatch")
        return dict(zip(parameters, arguments))

    if not isinstance(variadic_index, int) or isinstance(variadic_index, bool):
        raise ValueError("Invalid variadic parameter index")
    if variadic_index != len(parameters) - 1 or variadic_index < 0:
        raise ValueError("Variadic parameter must be last")
    if len(arguments) < variadic_index:
        raise ValueError("Missing required arguments before variadic parameter")
    fixed = dict(zip(parameters[:variadic_index], arguments[:variadic_index]))
    fixed[parameters[variadic_index]] = tuple(arguments[variadic_index:])
    return fixed
