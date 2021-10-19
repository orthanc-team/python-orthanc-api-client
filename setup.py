import subprocess

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

# FLAKE8_COMMAND = ['./venv/bin/flake8', '--ignore=E501', 'pyorthanc', 'tests']
# MYPY_COMMAND = ['./venv/bin/mypy', '--config-file=./mypy.ini', 'pyorthanc']
TESTS_COMMAND = ['./.venv/bin/python', '-m', 'unittest', 'discover', '-s', 'tests']


def _run_command(command: str) -> None:
    try:
        subprocess.check_call(command)

    except subprocess.CalledProcessError as error:
        print('Command failed with exit code', error.returncode)
        exit(error.returncode)


class Tests(TestCommand):
    description = 'run tests'
    user_options = []

    def run_tests(self):
        _run_command(TESTS_COMMAND)


class LintTests(TestCommand):
    description = 'run linters'
    user_options = []

    def run_tests(self):
        _run_command(FLAKE8_COMMAND)
        _run_command(MYPY_COMMAND)


class AllTests(TestCommand):
    description = 'run tests and linters'
    user_options = []

    def run_tests(self):
        _run_command(TESTS_COMMAND)
        # _run_command(FLAKE8_COMMAND)
        # _run_command(MYPY_COMMAND)


with open('./README.md', 'r') as file_handler:
    long_description = file_handler.read()


setup(
    name='orthanc_api_client',
    version='0.0.1',
    packages=find_packages(),
    url='https://todo',
    license='MIT',
    author='Alain Mazy',
    author_email='alain@mazy.be',
    description='Python Orthanc REST API client',
    long_description=long_description,
    install_requires=['urllib3', 'requests'],
    cmdclass={
        # 'lint': LintTests,
        # 'acceptance': Tests,
        'test': AllTests
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Healthcare Industry',
        'License :: OSI Approved :: LGPL v3',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
    ]
)
