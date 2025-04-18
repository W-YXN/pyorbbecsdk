import os
import re
import sys
import platform
import subprocess
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext

# A CMakeExtension that holds no source files,
# as our sources are built via CMake.


class CMakeExtension(Extension):
    def __init__(self, name, sourcedir=''):
        super().__init__(name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir)

# A custom build_ext command that calls CMake.


class CMakeBuild(build_ext):
    def run(self):
        # Ensure CMake is installed.
        try:
            subprocess.check_output(['cmake', '--version'])
        except OSError:
            raise RuntimeError("CMake must be installed to build the following extensions: " +
                               ", ".join(e.name for e in self.extensions))
        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):
        extdir = os.path.abspath(os.path.dirname(
            self.get_ext_fullpath(ext.name)))
        # Try to get the pybind11 directory using pybind11-config, but have a fallback mechanism
        try:
            pybind11_dir = subprocess.check_output(
                ['pybind11-config', '--cmakedir']).decode().strip()
        except Exception as e:
            # Fallback: try to find pybind11 through Python's package system
            try:
                import pybind11
                pybind11_dir = pybind11.get_cmake_dir()
            except Exception:
                raise RuntimeError(
                    "Failed to find pybind11 CMake dir. Make sure pybind11 is installed.")

        # Configure cmake arguments.
        cmake_args = [
            f'-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={extdir}',
            f'-DPYTHON_EXECUTABLE={sys.executable}',
            # Incorporates the build command flag.
            f'-Dpybind11_DIR={pybind11_dir}',
        ]

        cfg = 'Debug' if self.debug else 'Release'
        build_args = ['--config', cfg]

        if platform.system() == "Windows":
            cmake_args += [f'-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_{cfg.upper()}={extdir}']
            if sys.maxsize > 2**32:
                cmake_args += ['-A', 'x64']
            build_args += ['--', '/m']
        else:
            cmake_args += [f'-DCMAKE_BUILD_TYPE={cfg}']
            build_args += ['--', '-j2']

        # Create the build directory if it doesn't exist.
        build_temp = os.path.abspath(self.build_temp)
        os.makedirs(build_temp, exist_ok=True)

        # Run CMake configuration.
        subprocess.check_call(['cmake', ext.sourcedir] +
                              cmake_args, cwd=build_temp)
        # Build the project.
        subprocess.check_call(['cmake', '--build', '.'] +
                              build_args, cwd=build_temp)


# Use setuptools setup with minimal configuration since most metadata is in pyproject.toml
setup(
    ext_modules=[CMakeExtension('pyorbbecsdk', sourcedir='.')],
    cmdclass={'build_ext': CMakeBuild},
    zip_safe=False,
)

