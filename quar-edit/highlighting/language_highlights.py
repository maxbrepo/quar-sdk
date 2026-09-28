from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path
from build.build_profiles import profile_for_path

@dataclass(frozen=True)
class HighlightSpec:
    keywords: tuple[str,...]=()
    types: tuple[str,...]=()
    builtins: tuple[str,...]=()
    directives: tuple[str,...]=()

COMMON={
"c": HighlightSpec(("if","else","for","while","do","switch","case","break","continue","return","struct","typedef","enum","union","const","static","extern","sizeof"),("void","char","short","int","long","float","double","signed","unsigned","bool"),("printf","scanf","malloc","free","memcpy","strlen"),("#include","#define","#ifdef","#ifndef","#endif","#pragma")),
"cpp": HighlightSpec(("if","else","for","while","switch","case","break","continue","return","class","struct","namespace","using","template","public","private","protected","virtual","override","const","static","new","delete"),("void","bool","char","short","int","long","float","double","auto","string"),("cout","cin","endl","move","make_unique","make_shared"),("#include","#define","#ifdef","#endif","#pragma")),
"python": HighlightSpec(("if","elif","else","for","while","break","continue","return","def","class","import","from","as","try","except","finally","with","lambda","yield","async","await","match","case","pass","raise"),("int","float","str","bool","bytes","list","tuple","dict","set","object","None"),("print","len","range","open","enumerate","zip","sum","min","max","isinstance","super"),()),
"rust": HighlightSpec(("fn","let","mut","if","else","match","loop","while","for","in","return","struct","enum","impl","trait","use","mod","pub","crate","async","await","move","unsafe","where"),("i8","i16","i32","i64","i128","u8","u16","u32","u64","u128","f32","f64","bool","char","str","String","Vec","Option","Result"),("println","print","dbg","format","panic","todo","unimplemented"),()),
"freebasic": HighlightSpec(
    ("if","then","else","elseif","end","for","next","while","wend","do","loop","select","case","exit","continue","function","sub","return","dim","redim","const","type","enum","union","namespace","using","declare","static","shared","byval","byref","as"),
    ("byte","ubyte","short","ushort","integer","uinteger","long","ulong","longint","ulongint","single","double","string","zstring","wstring","boolean","any","object"),
    ("print","input","open","close","len","mid","left","right","chr","asc","val","str","ubound","lbound","cint","cdbl","csng"),
    ("#include","#define","#ifdef","#ifndef","#endif","#pragma","#lang")),
"go": HighlightSpec(("package","import","func","var","const","type","struct","interface","if","else","for","range","switch","case","select","go","defer","return","break","continue","fallthrough","map","chan"),("bool","string","byte","rune","int","int64","uint","float32","float64","complex64","complex128"),("make","new","len","cap","append","copy","delete","close","panic","recover","print","println"),()),
"zig": HighlightSpec(("const","var","fn","if","else","while","for","switch","return","break","continue","defer","errdefer","try","catch","orelse","struct","enum","union","error","comptime","pub","export","extern"),("bool","u8","u16","u32","u64","i8","i16","i32","i64","usize","isize","f32","f64","void","anytype"),("@import","@intCast","@floatCast","@sizeOf","@TypeOf"),()),
"java": HighlightSpec(("class","interface","enum","record","extends","implements","public","private","protected","static","final","abstract","if","else","for","while","switch","case","return","try","catch","finally","throw","throws","new","package","import","this","super"),("void","boolean","byte","short","int","long","float","double","char","String"),("System","Math","Objects","Arrays","Collections"),()),
"javascript": HighlightSpec(("const","let","var","function","class","extends","if","else","for","while","switch","case","return","try","catch","finally","throw","new","import","export","from","async","await","yield","typeof","instanceof"),("string","number","boolean","bigint","symbol","object","undefined","null"),("console","Math","JSON","Object","Array","Promise","Map","Set"),()),
"typescript": HighlightSpec(("const","let","var","function","class","interface","type","enum","namespace","extends","implements","if","else","for","while","return","import","export","from","async","await","public","private","protected","readonly","abstract"),("string","number","boolean","bigint","symbol","object","unknown","never","void","any"),("console","Math","JSON","Object","Array","Promise","Map","Set"),()),
"pascal": HighlightSpec(("program","unit","interface","implementation","uses","begin","end","if","then","else","for","to","downto","while","do","repeat","until","case","of","procedure","function","var","const","type","record","class","private","public"),("integer","int64","real","double","boolean","char","string","byte","word","pointer"),("writeln","write","readln","read","length","setlength","ord","chr"),()),
"assembly": HighlightSpec(("section","global","extern","bits","default"),("byte","word","dword","qword","oword","yword","zword"),("mov","lea","push","pop","call","ret","jmp","je","jne","jg","jl","cmp","test","add","sub","mul","imul","div","idiv","and","or","xor","shl","shr","nop","syscall"),()),
"mojo": HighlightSpec(("fn","def","struct","trait","var","let","alias","if","elif","else","for","while","return","import","from","as","try","raise"),("Int","Int32","Int64","UInt","Float32","Float64","Bool","String"),("print","len","range"),()),
"visual_quar": HighlightSpec(("if","else","return","while","for","state","switch","case","break","continue"),("int","float","bool","string","char","void"),("print",),()),
}

def spec_for_path(path: Path|None):
    p=profile_for_path(path)
    return COMMON.get(p.language_id) if p else None

def token_pattern(words):
    """Return a regex matching complete language words."""
    return re.compile(r"\\b(?:"+"|".join(re.escape(w) for w in words)+r")\\b") if words else None
