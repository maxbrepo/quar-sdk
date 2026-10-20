from .tokens import TokenType
from .errors import ParserError
from .numeric_types import canonical_numeric_type, INTEGER_BITS, FLOAT_BITS

from .ast_nodes import (
    Integer,
    Double,
    Boolean,
    Variable,
    BinaryOperation,
    UnaryOperation,
    VariableDeclaration,
    ConstantDeclaration,
    Assignment,
    FunctionCall,
    WithFileStatement,
    TryCatchStatement, ThrowStatement,
    NamedArgument,
    FunctionParameter,
    ReturnStatement,
    FunctionDefinition,
    IfStatement,
    WhileStatement,
    ForStatement,
    LoopStatement,
    ArrayDeclaration,
    ArrayAccess,
    ArrayAssignment,
    Char,
    String,
    TypeField,
    StructDefinition,
    RecordDefinition,
    EnumDefinition,
    ObjectDeclaration,
    ClassDefinition, ClassField, ClassConstructor, ClassMethod,
    MemberAccess,
    MemberAssignment,
    DoWhileStatement,
    BreakStatement,
    ContinueStatement,
    SwitchCase,
    SwitchStatement,
    TypeAlias,
    ImportStatement,
    TupleLiteral, TupleDeclaration, DestructuringDeclaration,
    EnumVariant, VariantConstructor, MatchArm, MatchStatement,
)


class Parser:

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        return self.tokens[self.pos]

    def advance(self):
        token = self.current()
        if token.type != TokenType.EOF:
            self.pos += 1
        return token

    def expect(self, token_type):
        token = self.current()
        if token.type != token_type:
            raise ParserError(
                f"Line {token.line}: expected {token_type.name}, "
                f"found {token.type.name}"
            )
        return self.advance()

    def parse(self):
        statements = []
        while self.current().type != TokenType.EOF:
            statements.append(self.parse_statement())
        return statements

    def parse_statement(self):
        token = self.current()

        primitive_types = (
            TokenType.TYPE_INT,
            TokenType.TYPE_I8,
            TokenType.TYPE_I16,
            TokenType.TYPE_I32,
            TokenType.TYPE_I64,
            TokenType.TYPE_I128,
            TokenType.TYPE_U8,
            TokenType.TYPE_BYTE,
            TokenType.TYPE_U16,
            TokenType.TYPE_U32,
            TokenType.TYPE_U64,
            TokenType.TYPE_U128,
            TokenType.TYPE_F32,
            TokenType.TYPE_F64,
            TokenType.TYPE_DOUBLE,
            TokenType.TYPE_BOOL,
            TokenType.TYPE_CHAR,
            TokenType.TYPE_STRING, TokenType.TYPE_BYTES,
            TokenType.TYPE_SHORT,
            TokenType.TYPE_USHORT,
            TokenType.TYPE_UINT,
            TokenType.TYPE_LONG,
            TokenType.TYPE_ULONG,
            TokenType.TYPE_LLONG,
            TokenType.TYPE_ULLONG,
            TokenType.TYPE_LONG_DOUBLE,
        )

        if token.type == TokenType.TYPE_TUPLE:
            return self.parse_tuple_declaration()
        if token.type == TokenType.LEFT_PAREN:
            return self.parse_destructuring_declaration()
        if token.type == TokenType.MATCH:
            return self.parse_match_statement()

        if token.type == TokenType.TRY:
            return self.parse_try_catch()
        if token.type == TokenType.THROW:
            self.advance()
            message = self.parse_expression()
            cause = None
            if self.current().type == TokenType.FROM:
                self.advance()
                cause = self.parse_expression()
            self.expect(TokenType.END_STMT)
            return ThrowStatement(message, cause)

        if token.type == TokenType.WITH:
            return self.parse_with_file()

        if token.type == TokenType.CONST:
            return self.parse_constant_declaration()

        if token.type == TokenType.IMPORT:
            return self.parse_import_statement()

        if token.type in primitive_types:
            type_offset = 2 if self.tokens[self.pos + 1].type == TokenType.QUESTION else 1
            if (
                self.tokens[self.pos + type_offset].type == TokenType.IDENTIFIER
                and self.tokens[self.pos + type_offset + 1].type == TokenType.LEFT_PAREN
            ):
                return self.parse_function_definition()
            return self.parse_variable_declaration()

        if token.type == TokenType.TYPE_VOID:
            return self.parse_function_definition()

        if token.type == TokenType.CLASS:
            return self.parse_class_definition()

        if token.type in (TokenType.STRUCT, TokenType.RECORD):
            return self.parse_composite_definition()

        if token.type == TokenType.ENUM:
            return self.parse_enum_definition()

        if token.type == TokenType.ALIAS:
            return self.parse_type_alias()

        if token.type == TokenType.SWITCH:
            return self.parse_switch_statement()

        if token.type == TokenType.CASE:
            return self.parse_case_statement()

        if token.type == TokenType.BREAK:
            self.advance()
            self.expect(TokenType.END_STMT)
            return BreakStatement()

        if token.type == TokenType.CONTINUE:
            self.advance()
            self.expect(TokenType.END_STMT)
            return ContinueStatement()

        if token.type == TokenType.IF:
            return self.parse_if_statement()

        if token.type == TokenType.DO:
            return self.parse_do_while_statement()

        if token.type == TokenType.WHILE:
            return self.parse_while_statement()

        if token.type == TokenType.FOR:
            return self.parse_for_statement()

        if token.type == TokenType.LOOP:
            return self.parse_loop_statement()

        if token.type == TokenType.RETURN:
            return self.parse_return_statement()

        if token.type in (TokenType.IDENTIFIER, TokenType.THIS):
            next_token = self.tokens[self.pos + 1]
            if (
                next_token.type == TokenType.IDENTIFIER
                and self.tokens[self.pos + 2].type == TokenType.LEFT_PAREN
            ):
                return self.parse_function_definition()
            if next_token.type == TokenType.IDENTIFIER:
                return self.parse_object_declaration()
            if next_token.type == TokenType.DOT:
                if self.is_qualified_function_call():
                    call = self.parse_qualified_function_call()
                    self.expect(TokenType.END_STMT)
                    return call
                return self.parse_member_assignment()
            if next_token.type == TokenType.LEFT_BRACKET:
                return self.parse_array_assignment()
            if next_token.type in (
                TokenType.ASSIGN,
                TokenType.PLUS_ASSIGN,
                TokenType.MINUS_ASSIGN,
                TokenType.MULTIPLY_ASSIGN,
                TokenType.DIVIDE_ASSIGN,
                TokenType.MODULO_ASSIGN,
            ):
                return self.parse_assignment()
            if next_token.type == TokenType.LEFT_PAREN:
                call = self.parse_function_call()
                self.expect(TokenType.END_STMT)
                return call

        raise ParserError(f"Line {token.line}: unrecognized statement")

    def parse_import_statement(self):
        self.expect(TokenType.IMPORT)
        parts = [self.advance().value]

        while self.current().type == TokenType.DOT:
            self.advance()
            parts.append(self.expect(TokenType.IDENTIFIER).value)

        alias = None
        if self.current().type == TokenType.AS:
            self.advance()
            alias = self.expect(TokenType.IDENTIFIER).value

        self.expect(TokenType.END_STMT)
        return ImportStatement(".".join(parts), alias)
        # Return module import declaration

    def is_qualified_function_call(self):
        index = self.pos

        while (
            index + 2 < len(self.tokens)
            and self.tokens[index + 1].type == TokenType.DOT
            and self.tokens[index + 2].type == TokenType.IDENTIFIER
        ):
            index += 2

        return (
            index + 1 < len(self.tokens)
            and self.tokens[index + 1].type == TokenType.LEFT_PAREN
        )

    def parse_qualified_function_call(self):
        parts = [self.advance().value]

        while self.current().type == TokenType.DOT:
            self.advance()
            parts.append(self.expect(TokenType.IDENTIFIER).value)

        self.expect(TokenType.LEFT_PAREN)
        arguments = []

        if self.current().type != TokenType.RIGHT_PAREN:
            arguments.append(self.parse_call_argument())
            while self.current().type == TokenType.COMMA:
                self.advance()
                arguments.append(self.parse_call_argument())

        self.expect(TokenType.RIGHT_PAREN)
        return FunctionCall(".".join(parts), arguments)
        # Return namespaced function call

    def parse_class_definition(self):
        self.expect(TokenType.CLASS)
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.LEFT_BRACE)
        fields = []
        methods = []
        constructor = None
        while self.current().type != TokenType.RIGHT_BRACE:
            visibility = "private"
            if self.current().type in (TokenType.PUBLIC, TokenType.PRIVATE):
                visibility = self.advance().value
            if self.current().type == TokenType.INIT:
                if constructor is not None:
                    raise ParserError("Duplicate class constructor")
                self.advance()
                self.expect(TokenType.LEFT_PAREN)
                parameters = self.parse_parameter_list()
                constructor = ClassConstructor(parameters, self.parse_block(), visibility)
                continue
            member_type = self.parse_type_name(allow_void=True)
            member_name = self.expect(TokenType.IDENTIFIER).value
            if self.current().type == TokenType.LEFT_PAREN:
                self.advance()
                parameters = self.parse_parameter_list()
                function = FunctionDefinition(member_type, member_name, parameters, self.parse_block())
                methods.append(ClassMethod(function, visibility))
            else:
                if member_type == "void":
                    raise ParserError("Class field cannot have void type")
                self.expect(TokenType.END_STMT)
                fields.append(ClassField(member_type, member_name, visibility))
        self.expect(TokenType.RIGHT_BRACE)
        return ClassDefinition(name, fields, constructor, methods)

    def parse_parameter_list(self):
        parameters = []
        if self.current().type != TokenType.RIGHT_PAREN:
            parameters.append(self.parse_function_parameter())
            while self.current().type == TokenType.COMMA:
                self.advance()
                parameters.append(self.parse_function_parameter())
        self.expect(TokenType.RIGHT_PAREN)
        return parameters

    def parse_composite_definition(self):
        kind = self.advance().type
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.LEFT_BRACE)
        fields = []

        while self.current().type != TokenType.RIGHT_BRACE:
            field_type = self.parse_type_name()
            field_name = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.END_STMT)
            fields.append(TypeField(field_type, field_name))

        self.expect(TokenType.RIGHT_BRACE)
        if kind == TokenType.STRUCT:
            return StructDefinition(name, fields)
        return RecordDefinition(name, fields)
        # Return composite type definition


    def parse_enum_definition(self):
        self.expect(TokenType.ENUM)
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.LEFT_BRACE)
        members = []
        while self.current().type != TokenType.RIGHT_BRACE:
            member_name = self.expect(TokenType.IDENTIFIER).value
            payload_types = []
            if self.current().type == TokenType.LEFT_PAREN:
                self.advance()
                if self.current().type != TokenType.RIGHT_PAREN:
                    payload_types.append(self.parse_type_name())
                    while self.current().type == TokenType.COMMA:
                        self.advance(); payload_types.append(self.parse_type_name())
                self.expect(TokenType.RIGHT_PAREN)
            members.append(EnumVariant(member_name, payload_types))
            if self.current().type == TokenType.COMMA: self.advance()
            elif self.current().type != TokenType.RIGHT_BRACE:
                raise ParserError(f"Line {self.current().line}: expected comma")
        self.expect(TokenType.RIGHT_BRACE)
        return EnumDefinition(name, members)

    def parse_tuple_declaration(self):
        self.expect(TokenType.TYPE_TUPLE)
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.ASSIGN)
        value = self.parse_expression()
        if not isinstance(value, TupleLiteral): raise ParserError("Tuple declaration requires tuple value")
        self.expect(TokenType.END_STMT)
        return TupleDeclaration(name, value)

    def parse_destructuring_declaration(self):
        self.expect(TokenType.LEFT_PAREN); bindings=[]
        while True:
            bindings.append((self.parse_type_name(), self.expect(TokenType.IDENTIFIER).value))
            if self.current().type != TokenType.COMMA: break
            self.advance()
        self.expect(TokenType.RIGHT_PAREN); self.expect(TokenType.ASSIGN)
        value=self.parse_expression(); self.expect(TokenType.END_STMT)
        return DestructuringDeclaration(bindings, value)

    def parse_match_statement(self):
        self.expect(TokenType.MATCH); self.expect(TokenType.LEFT_PAREN)
        expression=self.parse_expression(); self.expect(TokenType.RIGHT_PAREN); self.expect(TokenType.LEFT_BRACE)
        arms=[]; default_body=[]
        while self.current().type != TokenType.RIGHT_BRACE:
            if self.current().type == TokenType.DEFAULT:
                self.advance(); default_body=self.parse_block(); continue
            variant_name=self.expect(TokenType.IDENTIFIER).value; bindings=[]
            if self.current().type == TokenType.LEFT_PAREN:
                self.advance()
                if self.current().type != TokenType.RIGHT_PAREN:
                    bindings.append(self.expect(TokenType.IDENTIFIER).value)
                    while self.current().type == TokenType.COMMA:
                        self.advance(); bindings.append(self.expect(TokenType.IDENTIFIER).value)
                self.expect(TokenType.RIGHT_PAREN)
            arms.append(MatchArm(variant_name, bindings, self.parse_block()))
        self.expect(TokenType.RIGHT_BRACE)
        return MatchStatement(expression, arms, default_body)

    def parse_object_declaration(self):
        type_name = self.expect(TokenType.IDENTIFIER).value
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.ASSIGN)

        if self.current().type == TokenType.LEFT_BRACE:
            self.advance()
            arguments = []
            if self.current().type != TokenType.RIGHT_BRACE:
                arguments.append(self.parse_expression())
                while self.current().type == TokenType.COMMA:
                    self.advance()
                    arguments.append(self.parse_expression())
            self.expect(TokenType.RIGHT_BRACE)
            self.expect(TokenType.END_STMT)
            return ObjectDeclaration(type_name, name, arguments)
            # Return composite object declaration

        value = self.parse_expression()
        self.expect(TokenType.END_STMT)
        if isinstance(value, FunctionCall) and value.name == type_name:
            return ObjectDeclaration(type_name, name, value.arguments)
        return VariableDeclaration(type_name, name, value)
        # Return custom typed declaration

    def parse_member_assignment(self):
        object_name = self.advance().value
        self.expect(TokenType.DOT)
        member_name = self.expect(TokenType.IDENTIFIER).value
        assignment = self.advance()
        operators = {
            TokenType.PLUS_ASSIGN: "+",
            TokenType.MINUS_ASSIGN: "-",
            TokenType.MULTIPLY_ASSIGN: "*",
            TokenType.DIVIDE_ASSIGN: "/",
            TokenType.MODULO_ASSIGN: "%",
        }
        if assignment.type not in (TokenType.ASSIGN, *operators):
            raise ParserError(
                f"Line {assignment.line}: invalid member assignment"
            )
        value = self.parse_expression()
        self.expect(TokenType.END_STMT)
        if assignment.type in operators:
            value = BinaryOperation(
                MemberAccess(object_name, member_name),
                operators[assignment.type],
                value,
            )
        return MemberAssignment(object_name, member_name, value)

    def parse_for_statement(self):
        self.expect(TokenType.FOR)
        self.expect(TokenType.LEFT_PAREN)

        counter_name = self.expect(
            TokenType.IDENTIFIER
        ).value
        self.expect(TokenType.ASSIGN)
        start = self.parse_expression()
        self.expect(TokenType.END_STMT)

        comparison = self.parse_expression()
        step = 1
        direction = 0

        if self.current().type == TokenType.END_STMT:
            self.advance()
            step_token = self.expect(TokenType.INTEGER)
            step = int(step_token.value)
            if self.current().type == TokenType.PLUS:
                self.advance()
                self.expect(TokenType.PLUS)
                direction = 1
            elif self.current().type == TokenType.MINUS:
                self.advance()
                self.expect(TokenType.MINUS)
                direction = -1
            else:
                raise ParserError(
                    f"Line {self.current().line}: "
                    "for step requires N++ or N--"
                )

        self.expect(TokenType.RIGHT_PAREN)
        body = self.parse_block()

        return ForStatement(
            counter_name,
            start,
            comparison,
            body,
            step,
            direction,
        )
        # Return counter loop statement

    def parse_loop_statement(self):
        self.expect(TokenType.LOOP)
        return LoopStatement(self.parse_block())
        # Return explicit infinite loop

    def parse_type_alias(self):
        self.expect(TokenType.ALIAS)
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.ASSIGN)

        type_names = {
            TokenType.TYPE_INT: "int",
            TokenType.TYPE_I8: "i8",
            TokenType.TYPE_I16: "i16",
            TokenType.TYPE_I32: "i32",
            TokenType.TYPE_I64: "i64",
            TokenType.TYPE_I128: "i128",
            TokenType.TYPE_U8: "u8",
            TokenType.TYPE_BYTE: "byte",
            TokenType.TYPE_U16: "u16",
            TokenType.TYPE_U32: "u32",
            TokenType.TYPE_U64: "u64",
            TokenType.TYPE_U128: "u128",
            TokenType.TYPE_F32: "f32",
            TokenType.TYPE_F64: "f64",
            TokenType.TYPE_DOUBLE: "double",
            TokenType.TYPE_BOOL: "bool",
            TokenType.TYPE_CHAR: "char",
            TokenType.TYPE_STRING: "string",
            TokenType.TYPE_BYTES: "bytes",
            TokenType.TYPE_SHORT: "short",
            TokenType.TYPE_USHORT: "ushort",
            TokenType.TYPE_UINT: "uint",
            TokenType.TYPE_LONG: "long",
            TokenType.TYPE_ULONG: "ulong",
            TokenType.TYPE_LLONG: "llong",
            TokenType.TYPE_ULLONG: "ullong",
            TokenType.TYPE_LONG_DOUBLE: "long_double",
        }

        target = self.advance()
        if target.type in type_names:
            target_type = type_names[target.type]
        elif target.type == TokenType.IDENTIFIER:
            target_type = target.value
        else:
            raise ParserError(
                f"Line {target.line}: invalid alias target"
            )

        self.expect(TokenType.END_STMT)
        return TypeAlias(name, target_type)
        # Return type alias declaration

    def parse_switch_statement(self):
        self.expect(TokenType.SWITCH)
        self.expect(TokenType.LEFT_PAREN)
        expression = self.parse_expression()
        self.expect(TokenType.RIGHT_PAREN)
        self.expect(TokenType.LEFT_BRACE)

        cases = []
        default_body = []

        while self.current().type != TokenType.RIGHT_BRACE:
            if self.current().type == TokenType.CASE:
                self.advance()
                value = self.parse_expression()
                body = self.parse_block()
                cases.append(SwitchCase(value, body))
                continue

            if self.current().type == TokenType.DEFAULT:
                if default_body:
                    raise ParserError(
                        "Duplicate default"
                    )
                self.advance()
                default_body = self.parse_block()
                continue

            token = self.current()
            raise ParserError(
                f"Line {token.line}: expected CASE or DEFAULT"
            )

        self.expect(TokenType.RIGHT_BRACE)
        return SwitchStatement(expression, cases, default_body)
        # Return isolated switch cases


    def parse_case_statement(self):
        self.expect(TokenType.CASE)
        self.expect(TokenType.LEFT_PAREN)
        expression = self.parse_expression()
        self.expect(TokenType.RIGHT_PAREN)
        self.expect(TokenType.LEFT_BRACE)

        cases = []
        default_body = []

        while self.current().type != TokenType.RIGHT_BRACE:
            if self.current().type == TokenType.DEFAULT:
                if default_body:
                    raise ParserError(
                        "Duplicate default"
                    )
                self.advance()
                default_body = self.parse_block()
                continue

            value = self.parse_expression()
            body = self.parse_block()
            cases.append(SwitchCase(value, body))

        self.expect(TokenType.RIGHT_BRACE)
        return SwitchStatement(expression, cases, default_body)
        # Return compact value selection

    def parse_do_while_statement(self):
        self.expect(TokenType.DO)
        body = self.parse_block()
        self.expect(TokenType.WHILE)
        self.expect(TokenType.LEFT_PAREN)
        condition = self.parse_expression()
        self.expect(TokenType.RIGHT_PAREN)
        self.expect(TokenType.END_STMT)
        return DoWhileStatement(body, condition)
        # Return post-test loop statement

    def parse_while_statement(self):
        self.expect(TokenType.WHILE)
        self.expect(TokenType.LEFT_PAREN)
        condition = self.parse_expression()
        self.expect(TokenType.RIGHT_PAREN)
        body = self.parse_block()

        return WhileStatement(condition, body)
        # Return while loop statement

    def parse_if_statement(self):
        self.expect(TokenType.IF)
        self.expect(TokenType.LEFT_PAREN)
        condition = self.parse_expression()
        self.expect(TokenType.RIGHT_PAREN)
        then_body = self.parse_block()
        else_body = []

        if self.current().type == TokenType.ELSE:
            self.advance()
            if self.current().type == TokenType.IF:
                else_body = [self.parse_if_statement()]
            else:
                else_body = self.parse_block()

        return IfStatement(
            condition,
            then_body,
            else_body,
        )
        # Return conditional statement

    def parse_try_catch(self):
        self.expect(TokenType.TRY)
        try_body = self.parse_block()
        self.expect(TokenType.CATCH)
        self.expect(TokenType.LEFT_PAREN)
        error_name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.RIGHT_PAREN)
        catch_body = self.parse_block()
        return TryCatchStatement(try_body, error_name, catch_body)

    def parse_with_file(self):
        self.expect(TokenType.WITH)
        service = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.DOT)
        operation = self.expect(TokenType.IDENTIFIER).value
        if service != "File" or operation != "open":
            raise ParserError("with requires File.open")
        self.expect(TokenType.LEFT_PAREN)
        path = self.parse_expression()
        self.expect(TokenType.COMMA)
        mode = self.parse_expression()
        self.expect(TokenType.RIGHT_PAREN)
        self.expect(TokenType.AS)
        name = self.expect(TokenType.IDENTIFIER).value
        return WithFileStatement(path, mode, name, self.parse_block())

    def parse_block(self):
        self.expect(TokenType.LEFT_BRACE)
        statements = []

        while self.current().type != TokenType.RIGHT_BRACE:
            if self.current().type == TokenType.EOF:
                token = self.current()
                raise ParserError(
                    f"Line {token.line}: "
                    "expected RIGHT_BRACE, found EOF"
                )
            statements.append(self.parse_statement())

        self.expect(TokenType.RIGHT_BRACE)
        return statements
        # Return parsed statement block

    def parse_type_name(self, allow_void=False):
        token = self.advance()
        type_names = {
            TokenType.TYPE_INT: "int",
            TokenType.TYPE_I8: "i8",
            TokenType.TYPE_I16: "i16",
            TokenType.TYPE_I32: "i32",
            TokenType.TYPE_I64: "i64",
            TokenType.TYPE_I128: "i128",
            TokenType.TYPE_U8: "u8",
            TokenType.TYPE_BYTE: "byte",
            TokenType.TYPE_U16: "u16",
            TokenType.TYPE_U32: "u32",
            TokenType.TYPE_U64: "u64",
            TokenType.TYPE_U128: "u128",
            TokenType.TYPE_F32: "f32",
            TokenType.TYPE_F64: "f64",
            TokenType.TYPE_DOUBLE: "double",
            TokenType.TYPE_BOOL: "bool",
            TokenType.TYPE_CHAR: "char",
            TokenType.TYPE_STRING: "string",
            TokenType.TYPE_BYTES: "bytes",
            TokenType.TYPE_SHORT: "short",
            TokenType.TYPE_USHORT: "ushort",
            TokenType.TYPE_UINT: "uint",
            TokenType.TYPE_LONG: "long",
            TokenType.TYPE_ULONG: "ulong",
            TokenType.TYPE_LLONG: "llong",
            TokenType.TYPE_ULLONG: "ullong",
            TokenType.TYPE_LONG_DOUBLE: "long_double",
        }
        if allow_void:
            type_names[TokenType.TYPE_VOID] = "void"
        if token.type == TokenType.IDENTIFIER:
            type_name = token.value
        elif token.type in type_names:
            type_name = type_names[token.type]
        else:
            raise ParserError(
                f"Line {token.line}: expected type, found {token.type.name}"
            )
        if self.current().type == TokenType.QUESTION:
            if type_name == "void":
                raise ParserError(f"Line {token.line}: void cannot be optional")
            self.advance()
            if self.current().type == TokenType.QUESTION:
                raise ParserError(f"Line {self.current().line}: nested optional types are not supported")
            return type_name + "?"
        return type_name
        # Return canonical primitive or optional type

    def parse_function_definition(self):
        return_type = self.parse_type_name(allow_void=True)
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.LEFT_PAREN)
        parameters = []

        if self.current().type != TokenType.RIGHT_PAREN:
            parameters.append(self.parse_function_parameter())
            while self.current().type == TokenType.COMMA:
                self.advance()
                parameters.append(self.parse_function_parameter())

        self.expect(TokenType.RIGHT_PAREN)
        body = self.parse_block()
        return FunctionDefinition(return_type, name, parameters, body)
        # Return typed function definition

    def parse_function_parameter(self):
        var_type = self.parse_type_name()
        name = self.expect(TokenType.IDENTIFIER).value
        default_value = None
        if self.current().type == TokenType.ASSIGN:
            self.advance()
            default_value = self.parse_expression()
        return FunctionParameter(var_type, name, default_value)
        # Return typed function parameter

    def parse_call_argument(self):
        if (
            self.current().type == TokenType.IDENTIFIER
            and self.tokens[self.pos + 1].type == TokenType.ASSIGN
        ):
            name = self.advance().value
            self.advance()
            return NamedArgument(name, self.parse_expression())
        return self.parse_expression()
        # Return positional or named argument

    def parse_return_statement(self):
        self.expect(TokenType.RETURN)
        if self.current().type == TokenType.END_STMT:
            self.advance()
            return ReturnStatement(None)
        value = self.parse_expression()
        self.expect(TokenType.END_STMT)
        return ReturnStatement(value)
        # Return optional function result


    def parse_constant_declaration(self):
        self.expect(TokenType.CONST)

        primitive_types = {
            TokenType.TYPE_INT, TokenType.TYPE_DOUBLE,
            TokenType.TYPE_I8, TokenType.TYPE_I16, TokenType.TYPE_I32,
            TokenType.TYPE_I64, TokenType.TYPE_I128,
            TokenType.TYPE_U8, TokenType.TYPE_BYTE, TokenType.TYPE_U16, TokenType.TYPE_U32,
            TokenType.TYPE_U64, TokenType.TYPE_U128,
            TokenType.TYPE_F32, TokenType.TYPE_F64,
            TokenType.TYPE_BOOL, TokenType.TYPE_CHAR, TokenType.TYPE_STRING, TokenType.TYPE_BYTES,
            TokenType.TYPE_SHORT, TokenType.TYPE_USHORT, TokenType.TYPE_UINT,
            TokenType.TYPE_LONG, TokenType.TYPE_ULONG,
            TokenType.TYPE_LLONG, TokenType.TYPE_ULLONG,
            TokenType.TYPE_LONG_DOUBLE,
        }

        var_type = None
        if self.current().type in primitive_types:
            var_type = self.parse_type_name()

        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.ASSIGN)
        value = self.parse_expression()
        self.expect(TokenType.END_STMT)
        return ConstantDeclaration(var_type, name, value)
        # Return immutable constant declaration

    def parse_variable_declaration(self):
        var_type = self.parse_type_name()
        name = self.expect(TokenType.IDENTIFIER).value

        if self.current().type == TokenType.LEFT_BRACKET:
            self.advance()
            dynamic = self.current().type == TokenType.RIGHT_BRACKET
            size = None if dynamic else int(
                self.expect(TokenType.INTEGER).value
            )
            self.expect(TokenType.RIGHT_BRACKET)
            second_size = None

            if not dynamic and self.current().type == TokenType.LEFT_BRACKET:
                self.advance()
                second_size = int(
                    self.expect(TokenType.INTEGER).value
                )
                self.expect(TokenType.RIGHT_BRACKET)

            initial_values = None
            if self.current().type == TokenType.ASSIGN:
                self.advance()
                self.expect(TokenType.LEFT_BRACE)
                initial_values = []
                if self.current().type != TokenType.RIGHT_BRACE:
                    initial_values.append(self.parse_expression())
                    while self.current().type == TokenType.COMMA:
                        self.advance()
                        initial_values.append(self.parse_expression())
                self.expect(TokenType.RIGHT_BRACE)

            self.expect(TokenType.END_STMT)
            return ArrayDeclaration(
                var_type,
                name,
                size,
                initial_values,
                second_size,
                dynamic,
            )
            # Return typed array declaration

        if self.current().type == TokenType.ASSIGN:
            self.advance()
            value = self.parse_expression()
        else:
            defaults = {
                "bool": Boolean(False),
                "char": Char(""),
                "string": String(""),
            }
            canonical = canonical_numeric_type(var_type)
            if canonical in INTEGER_BITS:
                value = Integer(0)
            elif canonical in FLOAT_BITS:
                value = Double(0.0)
            elif var_type in defaults:
                value = defaults[var_type]
            else:
                raise ParserError(
                    f"Line {self.current().line}: type '{var_type}' requires initialization"
                )
        self.expect(TokenType.END_STMT)
        return VariableDeclaration(var_type, name, value)


    def parse_array_assignment(self):
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.LEFT_BRACKET)
        index = self.parse_expression()
        self.expect(TokenType.RIGHT_BRACKET)
        second_index = None

        if self.current().type == TokenType.LEFT_BRACKET:
            self.advance()
            second_index = self.parse_expression()
            self.expect(TokenType.RIGHT_BRACKET)

        self.expect(TokenType.ASSIGN)
        value = self.parse_expression()
        self.expect(TokenType.END_STMT)
        return ArrayAssignment(
            name,
            index,
            value,
            second_index,
        )
        # Return array element assignment


    def parse_assignment(self):
        name = self.expect(TokenType.IDENTIFIER).value
        assignment = self.advance()
        value = self.parse_expression()
        self.expect(TokenType.END_STMT)

        compound_operators = {
            TokenType.PLUS_ASSIGN: "+",
            TokenType.MINUS_ASSIGN: "-",
            TokenType.MULTIPLY_ASSIGN: "*",
            TokenType.DIVIDE_ASSIGN: "/",
            TokenType.MODULO_ASSIGN: "%",
        }
        if assignment.type in compound_operators:
            value = BinaryOperation(
                Variable(name),
                compound_operators[assignment.type],
                value,
            )
        elif assignment.type != TokenType.ASSIGN:
            raise ParserError(
                f"Line {assignment.line}: invalid assignment"
            )
        return Assignment(name, value)
        # Return normalized assignment

    def parse_expression(self):
        return self.parse_or()

    def parse_or(self):
        left = self.parse_and()
        while self.current().type == TokenType.OR:
            operator = self.advance().value
            right = self.parse_and()
            left = BinaryOperation(left, operator, right)
        return left
        # Return logical OR expression

    def parse_and(self):
        left = self.parse_bitwise_or()
        while self.current().type == TokenType.AND:
            operator = self.advance().value
            right = self.parse_bitwise_or()
            left = BinaryOperation(left, operator, right)
        return left
        # Return logical AND expression

    def parse_bitwise_or(self):
        left = self.parse_bitwise_xor()
        while self.current().type == TokenType.BIT_OR:
            operator = self.advance().value
            right = self.parse_bitwise_xor()
            left = BinaryOperation(left, operator, right)
        return left
        # Return bitwise OR expression

    def parse_bitwise_xor(self):
        left = self.parse_bitwise_and()
        while self.current().type == TokenType.BIT_XOR:
            operator = self.advance().value
            right = self.parse_bitwise_and()
            left = BinaryOperation(left, operator, right)
        return left
        # Return bitwise XOR expression

    def parse_bitwise_and(self):
        left = self.parse_equality()
        while self.current().type == TokenType.BIT_AND:
            operator = self.advance().value
            right = self.parse_equality()
            left = BinaryOperation(left, operator, right)
        return left
        # Return bitwise AND expression

    def parse_equality(self):
        left = self.parse_relational()
        while self.current().type in (TokenType.EQUAL, TokenType.NOT_EQUAL):
            operator = self.advance().value
            right = self.parse_relational()
            left = BinaryOperation(left, operator, right)
        return left
        # Return equality expression

    def parse_relational(self):
        left = self.parse_shift()
        relational_tokens = (
            TokenType.LESS,
            TokenType.LESS_EQUAL,
            TokenType.GREATER,
            TokenType.GREATER_EQUAL,
        )
        while self.current().type in relational_tokens:
            operator = self.advance().value
            right = self.parse_shift()
            left = BinaryOperation(left, operator, right)
        return left
        # Return relational expression

    def parse_shift(self):
        left = self.parse_additive()
        while self.current().type in (
            TokenType.SHIFT_LEFT,
            TokenType.SHIFT_RIGHT,
        ):
            operator = self.advance().value
            right = self.parse_additive()
            left = BinaryOperation(left, operator, right)
        return left
        # Return shift expression

    def parse_additive(self):
        left = self.parse_term()
        while self.current().type in (TokenType.PLUS, TokenType.MINUS):
            operator = self.advance().value
            right = self.parse_term()
            left = BinaryOperation(left, operator, right)
        return left
        # Return additive expression

    def parse_term(self):
        left = self.parse_unary()
        while self.current().type in (
            TokenType.MULTIPLY,
            TokenType.DIVIDE,
            TokenType.MODULO,
        ):
            operator = self.advance().value
            right = self.parse_unary()
            left = BinaryOperation(left, operator, right)
        return left
        # Return multiplicative expression

    def parse_unary(self):
        token = self.current()
        if token.type == TokenType.NOT:
            self.advance()
            return UnaryOperation("not", self.parse_unary())
        if token.type == TokenType.MINUS:
            self.advance()
            return UnaryOperation("-", self.parse_unary())
        if token.type == TokenType.BIT_NOT:
            self.advance()
            return UnaryOperation("~", self.parse_unary())
        return self.parse_primary()
        # Return unary expression

    def parse_primary(self):
        token = self.current()

        if token.type == TokenType.CHAR:
            self.advance()
            return Char(token.value)

        if token.type == TokenType.STRING:
            self.advance()
            return String(token.value)

        if token.type == TokenType.INTEGER:
            self.advance()
            return Integer(int(token.value))

        if token.type == TokenType.DOUBLE:
            self.advance()
            return Double(float(token.value))

        if token.type == TokenType.TRUE:
            self.advance()
            return Boolean(True)

        if token.type == TokenType.FALSE:
            self.advance()
            return Boolean(False)

        if token.type in (TokenType.IDENTIFIER, TokenType.THIS):
            next_token = self.tokens[self.pos + 1]
            if next_token.type == TokenType.LEFT_PAREN:
                return self.parse_function_call()
            if next_token.type == TokenType.DOT:
                object_name = self.advance().value
                self.expect(TokenType.DOT)
                member_name = self.expect(TokenType.IDENTIFIER).value
                # Qualified function names may contain more than one namespace.
                if self.current().type == TokenType.DOT:
                    segments = [object_name, member_name]
                    while self.current().type == TokenType.DOT:
                        self.advance()
                        segments.append(self.expect(TokenType.IDENTIFIER).value)
                    if self.current().type == TokenType.LEFT_PAREN:
                        self.advance()
                        arguments = []
                        if self.current().type != TokenType.RIGHT_PAREN:
                            arguments.append(self.parse_call_argument())
                            while self.current().type == TokenType.COMMA:
                                self.advance()
                                arguments.append(self.parse_call_argument())
                        self.expect(TokenType.RIGHT_PAREN)
                        return FunctionCall(".".join(segments), arguments)
                    raise ParserError(f"Line {token.line}: qualified name requires a call")
                if self.current().type == TokenType.LEFT_PAREN:
                    self.advance(); arguments=[]
                    if self.current().type != TokenType.RIGHT_PAREN:
                        arguments.append(self.parse_expression())
                        while self.current().type == TokenType.COMMA:
                            self.advance(); arguments.append(self.parse_expression())
                    self.expect(TokenType.RIGHT_PAREN)
                    return VariantConstructor(object_name, member_name, arguments)
                return MemberAccess(object_name, member_name)
            if next_token.type == TokenType.LEFT_BRACKET:
                name = self.advance().value
                self.expect(TokenType.LEFT_BRACKET)
                index = self.parse_expression()
                self.expect(TokenType.RIGHT_BRACKET)
                second_index = None
                if self.current().type == TokenType.LEFT_BRACKET:
                    self.advance()
                    second_index = self.parse_expression()
                    self.expect(TokenType.RIGHT_BRACKET)
                return ArrayAccess(name, index, second_index)
                # Return indexed sequence access
            self.advance()
            return Variable(token.value)

        if token.type == TokenType.LEFT_PAREN:
            self.advance(); first = self.parse_expression()
            if self.current().type == TokenType.COMMA:
                values=[first]
                while self.current().type == TokenType.COMMA:
                    self.advance(); values.append(self.parse_expression())
                self.expect(TokenType.RIGHT_PAREN); return TupleLiteral(values)
            self.expect(TokenType.RIGHT_PAREN); return first

        raise ParserError(f"Line {token.line}: invalid expression")

    def parse_function_call(self):
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.LEFT_PAREN)
        arguments = []

        if self.current().type != TokenType.RIGHT_PAREN:
            arguments.append(self.parse_call_argument())
            while self.current().type == TokenType.COMMA:
                self.advance()
                arguments.append(self.parse_call_argument())

        self.expect(TokenType.RIGHT_PAREN)
        return FunctionCall(name, arguments)


# Source metadata is optional and never participates in AST equality or semantics.
def _record_source_span(method):
    """Decorate parser entry points with token-based, half-open source spans."""
    from functools import wraps

    @wraps(method)
    def wrapped(self, *args, **kwargs):
        first = self.current()
        initial_pos = self.pos
        node = method(self, *args, **kwargs)
        if self.pos <= initial_pos or not hasattr(node, "__dict__"):
            return node
        last = self.tokens[self.pos - 1]
        # Token text lengths are accurate for most lexemes; use the following
        # token's position when on the same line to include closing punctuation.
        end_line = last.line
        end_column = last.column + len(str(last.value))
        if self.pos < len(self.tokens):
            following = self.tokens[self.pos]
            if following.line == last.line and following.column > last.column:
                end_column = following.column
        if end_line > first.line or end_column > first.column:
            if getattr(node, "start", None) is None:
                node.start = (first.line, first.column)
            if getattr(node, "end", None) is None:
                node.end = (end_line, end_column)
        return node

    return wrapped


Parser.parse_statement = _record_source_span(Parser.parse_statement)
Parser.parse_expression = _record_source_span(Parser.parse_expression)
Parser.parse_primary = _record_source_span(Parser.parse_primary)
