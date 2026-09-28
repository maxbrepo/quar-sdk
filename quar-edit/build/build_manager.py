from __future__ import annotations
import platform, shutil, subprocess, time
from pathlib import Path
from build.build_profiles import BuildOperation, LanguageBuildProfile, get_operation, profile_for_path

class BuildResult:
    def __init__(self,title,command,output,return_code,duration_seconds=0.0):
        self.title=title; self.command=command; self.output=output
        self.return_code=return_code; self.duration_seconds=duration_seconds

class BuildManager:
    """Execute profile operations and measure their wall-clock duration."""
    def __init__(self):
        self.platform_name="windows" if platform.system()=="Windows" else "linux"

    def get_profile(self,file_path): return profile_for_path(file_path)

    def compile_debug(self,file_path):
        return self._execute(self._require_profile(file_path),
            get_operation(self._require_profile(file_path),("Compile Debug","Build Debug","Build Bytecode")),file_path)

    def compile_release(self,file_path):
        return self._execute(self._require_profile(file_path),
            get_operation(self._require_profile(file_path),("Compile Release","Build Release","Build Bytecode")),file_path)

    def build(self,file_path):
        """Use the normal optimized build/compile mode."""
        return self.compile_release(file_path)

    def run(self,file_path):
        """Interpret the source through its interpreter or virtual machine."""
        p=self._require_profile(file_path)
        return self._execute(p,get_operation(p,("Interpret",)),file_path)

    def build_and_run(self,file_path):
        first=self.build(file_path); results=[first]
        if first.return_code==0:
            p=self._require_profile(file_path)
            link=get_operation(p,("Link",))
            if link is not None:
                linked=self._execute(p,link,file_path); results.append(linked)
                if linked.return_code!=0: return results
            results.append(self.run(file_path))
        return results

    def _require_profile(self,file_path):
        p=self.get_profile(file_path)
        if p is None: raise ValueError(f"No build profile is associated with {file_path.suffix or 'this file'}.")
        if file_path.suffix.lower() in p.header_extensions:
            raise ValueError(f"{p.display_name} header files are recognized but are not compiled directly.")
        return p

    def _execute(self,p,operation,file_path):
        if operation is None: raise ValueError(f"{p.display_name} does not define this operation.")
        for tool in operation.required_tools:
            if shutil.which(tool) is None: raise RuntimeError(f"Required tool not found: {tool}")
        source=file_path.resolve(); output=source.with_suffix(""); obj=source.with_suffix(".o")
        vals={"source":str(source),"source_dir":str(source.parent),"filename":source.name,
              "basename":source.stem,"extension":source.suffix,"output":str(output),
              "object":str(obj),"project_dir":str(source.parent)}
        template=operation.windows if self.platform_name=="windows" else operation.linux
        command=template.format(**vals)
        started=time.perf_counter()
        completed=subprocess.run(command,cwd=source.parent,shell=True,text=True,capture_output=True)
        duration=time.perf_counter()-started
        combined=(completed.stdout or "")
        if completed.stderr:
            if combined and not combined.endswith("\n"): combined+="\n"
            combined+=completed.stderr
        return BuildResult(f"{p.display_name} - {operation.name}",command,combined.rstrip(),completed.returncode,duration)
