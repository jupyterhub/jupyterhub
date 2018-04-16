"""Windows utilities functions."""

import os
import ctypes
import win32process

from subprocess import Popen, list2cmdline, Handle

DWORD  = ctypes.c_uint
HANDLE = DWORD
BOOL = ctypes.wintypes.BOOL

CloseHandle = ctypes.windll.kernel32.CloseHandle
CloseHandle.argtypes = [HANDLE]
CloseHandle.restype = BOOL

class PopenAsUser(Popen):
    def __init__(self, args, bufsize=-1, executable=None,
                 stdin=None, stdout=None, stderr=None,
                 shell=False, cwd=None, env=None, universal_newlines=False,
                 startupinfo=None, creationflags=0,*, encoding=None,
                 errors=None, token=None):
        """Create new PopenAsUser instance."""
        self._token = token

        super(PopenAsUser, self).__init__(args, bufsize, executable,
                 stdin, stdout, stderr, None, False,
                 shell, cwd, env, universal_newlines,
                 startupinfo, creationflags, False, False, (),
				 encoding=encoding, errors=errors)

    def __exit__(self, type, value, traceback):
        # Detach to avoid invalidating underlying winhandle
        self._token.Detach()
        super(PopenAsUser, self).__exit__(self, type, value, traceback)

    # Mainly adapted from subprocess._execute_child, with the main exception that this
    # function calls CreateProcessAsUser instead of CreateProcess
    def _execute_child(self, args, executable, preexec_fn, close_fds,
                       pass_fds, cwd, env,
                       startupinfo, creationflags, shell,
                       p2cread, p2cwrite,
                       c2pread, c2pwrite,
                       errread, errwrite,
                       unused_restore_signals, unused_start_new_session):
        """Execute program"""

        assert not pass_fds, "pass_fds not supported on Windows."

        if not isinstance(args, str):
            args = list2cmdline(args)

        # Process startup details
        if startupinfo is None:
            startupinfo = win32process.STARTUPINFO()
        if -1 not in (p2cread, c2pwrite, errwrite):
            startupinfo.dwFlags |= win32process.STARTF_USESTDHANDLES
            startupinfo.hStdInput = p2cread
            startupinfo.hStdOutput = c2pwrite
            startupinfo.hStdError = errwrite

        if shell:
            startupinfo.dwFlags |= win32process.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = win32process.SW_HIDE
            comspec = os.environ.get("COMSPEC", "cmd.exe")
            args = '{} /c "{}"'.format (comspec, args)

        # Start the process
        try:
            hp, ht, pid, tid = win32process.CreateProcessAsUser(self._token, executable, args,
                                     # no special security
                                     None, None,
                                     int(not close_fds),
                                     creationflags,
                                     env,
                                     os.fspath(cwd) if cwd is not None else None,
                                     startupinfo)
        finally:
            # Child is launched. Close the parent's copy of those pipe
            # handles that only the child should have open.  You need
            # to make sure that no handles to the write end of the
            # output pipe are maintained in this process or else the
            # pipe will not close when the child process exits and the
            # ReadFile will hang.
            if p2cread != -1:
                p2cread.Close()
            if c2pwrite != -1:
                c2pwrite.Close()
            if errwrite != -1:
                errwrite.Close()
            if hasattr(self, '_devnull'):
                os.close(self._devnull)

        # Retain the process handle, but close the thread handle
        self._child_created = True
        # Popen stores the win handle as an int, not as a PyHandle
        self._handle = Handle(hp.Detach())
        self.pid = pid
        CloseHandle(ht)
