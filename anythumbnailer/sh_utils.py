
from __future__ import absolute_import

from io import BytesIO
import subprocess


__all__ = ['run', 'run_pipe', 'pipe_with_input']

def run(command_args, input_=None):
    stdin = subprocess.PIPE if (input_ is not None) else None
    if hasattr(input_, 'read'):
        input_ = input_.read()
    process = subprocess.Popen(command_args, stdout=subprocess.PIPE, stdin=stdin)
    stdout_data, stderr_data = process.communicate(input=input_)
    assert process.returncode == 0
    return BytesIO(stdout_data)

def run_pipe(input_=None, *commands):
    if isinstance(input_, (tuple, list)):
        commands = (input_, ) + commands
        input_ = None
    else:
        input_ = input_.read()
    assert len(commands) >= 1
    
    last_output_data = input_
    for command_args in commands:
        last_output_data = run(command_args, last_output_data)
    return last_output_data

def pipe_with_input(filename_or_fp, *commands):
    filename = None
    fp = None
    if hasattr(filename_or_fp, 'read'):
        fp = filename_or_fp
    else:
        filename = filename_or_fp
    
    first_command = commands[0]
    if filename:
        first_command = first_command + (filename, )
        return run_pipe(first_command, *commands[1:])
    return run_pipe(fp, *commands)

