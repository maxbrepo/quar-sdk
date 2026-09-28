from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class BuildOperation:
    name: str
    kind: str
    linux: str
    windows: str
    required_tools: tuple[str, ...] = ()
    optional: bool = False

@dataclass(frozen=True)
class LanguageBuildProfile:
    language_id: str
    display_name: str
    source_extensions: tuple[str, ...]
    header_extensions: tuple[str, ...] = ()
    compiler: str = ""
    interpreter: str = ""
    linker: str = ""
    operations: tuple[BuildOperation, ...] = ()

    @property
    def extensions(self) -> tuple[str, ...]:
        return self.source_extensions + self.header_extensions

def op(name, kind, linux, windows, *tools, optional=False):
    return BuildOperation(name, kind, linux, windows, tuple(tools), optional)

PROFILES = (
    LanguageBuildProfile("c","C",(".c",),(".h",),"gcc","","",(
        op("Compile Debug","EXE",'gcc -g -O0 "{source}" -o "{output}"','gcc -g -O0 "{source}" -o "{output}.exe"',"gcc"),
        op("Compile Release","EXE",'gcc -O2 "{source}" -o "{output}"','gcc -O2 "{source}" -o "{output}.exe"',"gcc"),
        op("Execute","EXE",'"{output}"','"{output}.exe"'))),
    LanguageBuildProfile("cpp","C++",(".cpp",".cc",".cxx"),(".hpp",".hh",".hxx"),"g++","","",(
        op("Compile Debug","EXE",'g++ -g -O0 "{source}" -o "{output}"','g++ -g -O0 "{source}" -o "{output}.exe"',"g++"),
        op("Compile Release","EXE",'g++ -O2 "{source}" -o "{output}"','g++ -O2 "{source}" -o "{output}.exe"',"g++"),
        op("Execute","EXE",'"{output}"','"{output}.exe"'))),
    LanguageBuildProfile("assembly","Assembly",(".asm",".s"),(),"nasm / as","","ld",(
        op("Compile Debug","OBJ",'nasm -f elf64 -g -F dwarf "{source}" -o "{object}"','nasm -f win64 -g "{source}" -o "{object}.obj"',"nasm"),
        op("Compile Release","OBJ",'nasm -f elf64 "{source}" -o "{object}"','nasm -f win64 "{source}" -o "{object}.obj"',"nasm"),
        op("Link","EXE",'ld "{object}" -o "{output}"','gcc "{object}.obj" -o "{output}.exe"',"ld"),
        op("Execute","EXE",'"{output}"','"{output}.exe"'))),
    LanguageBuildProfile("rust","Rust",(".rs",),(),"rustc","","",(
        op("Compile Debug","EXE",'rustc -C debuginfo=2 "{source}" -o "{output}"','rustc -C debuginfo=2 "{source}" -o "{output}.exe"',"rustc"),
        op("Compile Release","EXE",'rustc -O "{source}" -o "{output}"','rustc -O "{source}" -o "{output}.exe"',"rustc"),
        op("Execute","EXE",'"{output}"','"{output}.exe"'))),
    LanguageBuildProfile("pascal","Pascal",(".pas",".pp"),(),"fpc","","",(
        op("Compile Debug","EXE",'fpc -gl -O- "{source}" -o"{output}"','fpc -gl -O- "{source}" -o"{output}.exe"',"fpc"),
        op("Compile Release","EXE",'fpc -O2 "{source}" -o"{output}"','fpc -O2 "{source}" -o"{output}.exe"',"fpc"),
        op("Execute","EXE",'"{output}"','"{output}.exe"'))),
    LanguageBuildProfile("freebasic","FreeBASIC",(".bas",),(".bi",),"fbc","","",(
        op("Compile Debug","EXE",'fbc -g "{source}" -x "{output}"','fbc -g "{source}" -x "{output}.exe"',"fbc"),
        op("Compile Release","EXE",'fbc -O 2 "{source}" -x "{output}"','fbc -O 2 "{source}" -x "{output}.exe"',"fbc"),
        op("Execute","EXE",'"{output}"','"{output}.exe"'))),
    LanguageBuildProfile("go","Go",(".go",),(),"go","","",(
        op("Compile Debug","EXE",'go build -gcflags="all=-N -l" -o "{output}" "{source}"','go build -gcflags="all=-N -l" -o "{output}.exe" "{source}"',"go"),
        op("Compile Release","EXE",'go build -o "{output}" "{source}"','go build -o "{output}.exe" "{source}"',"go"),
        op("Execute","EXE",'"{output}"','"{output}.exe"'))),
    LanguageBuildProfile("zig","Zig",(".zig",),(),"zig","","",(
        op("Compile Debug","EXE",'zig build-exe -O Debug "{source}" -femit-bin="{output}"','zig build-exe -O Debug "{source}" -femit-bin="{output}.exe"',"zig"),
        op("Compile Release","EXE",'zig build-exe -O ReleaseFast "{source}" -femit-bin="{output}"','zig build-exe -O ReleaseFast "{source}" -femit-bin="{output}.exe"',"zig"),
        op("Execute","EXE",'"{output}"','"{output}.exe"'))),
    LanguageBuildProfile("java","Java",(".java",),(),"javac","java","",(
        op("Build Debug","ByteC",'javac -g "{source}"','javac -g "{source}"',"javac"),
        op("Build Release","ByteC",'javac -g:none "{source}"','javac -g:none "{source}"',"javac"),
        op("Interpret","ByteC",'java -cp "{source_dir}" "{basename}"','java -cp "{source_dir}" "{basename}"',"java"))),
    LanguageBuildProfile("python","Python",(".py",),(),"","python3","",(
        op("Build Bytecode","ByteC",'python3 -m py_compile "{source}"','python -m py_compile "{source}"',"python3"),
        op("Interpret","INT",'python3 "{source}"','python "{source}"',"python3"),
        op("Compile Debug","EXE",'python3 -m nuitka --debug "{source}"','python -m nuitka --debug "{source}"',"python3",optional=True),
        op("Compile Release","EXE",'python3 -m nuitka --onefile "{source}"','python -m nuitka --onefile "{source}"',"python3",optional=True))),
    LanguageBuildProfile("javascript","JavaScript",(".js",".mjs",".cjs"),(),"","node","",(
        op("Interpret","INT",'node "{source}"','node "{source}"',"node"),)),
    LanguageBuildProfile("typescript","TypeScript",(".ts",),(),"tsc","node","",(
        op("Compile Debug","JS",'tsc --sourceMap true "{source}"','tsc --sourceMap true "{source}"',"tsc"),
        op("Compile Release","JS",'tsc --sourceMap false "{source}"','tsc --sourceMap false "{source}"',"tsc"),
        op("Interpret","INT",'node "{source_dir}/{basename}.js"','node "{source_dir}/{basename}.js"',"node"))),
    LanguageBuildProfile("mojo","Mojo",(".mojo",),(),"mojo","mojo","",(
        op("Compile Debug","EXE",'mojo build "{source}" -o "{output}"','mojo build "{source}" -o "{output}.exe"',"mojo",optional=True),
        op("Compile Release","EXE",'mojo build "{source}" -o "{output}"','mojo build "{source}" -o "{output}.exe"',"mojo",optional=True),
        op("Interpret","INT",'mojo "{source}"','mojo "{source}"',"mojo",optional=True))),
    LanguageBuildProfile("visual_quar","Visual Quar",(".vq",),(),"vq","qrvm","",(
        op("Build Bytecode","ByteC",'vq build-bytecode "{source}"','vq build-bytecode "{source}"',"vq",optional=True),
        op("Interpret","ByteC",'qrvm "{output}"','qrvm "{output}"',"qrvm",optional=True),
        op("Compile Debug","EXE",'vq compile --debug "{source}" -o "{output}"','vq compile --debug "{source}" -o "{output}.exe"',"vq",optional=True),
        op("Compile Release","EXE",'vq compile --release "{source}" -o "{output}"','vq compile --release "{source}" -o "{output}.exe"',"vq",optional=True),
        op("Execute","EXE",'"{output}"','"{output}.exe"',optional=True))),
)

def profile_for_path(file_path: Path | None):
    if file_path is None: return None
    suffix=file_path.suffix.lower()
    return next((p for p in PROFILES if suffix in p.extensions),None)

def get_operation(profile, names):
    for name in names:
        for operation in profile.operations:
            if operation.name == name: return operation
    return None
