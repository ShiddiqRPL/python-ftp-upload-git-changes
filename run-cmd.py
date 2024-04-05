import ftplib
import os
import sys
import time

from enum import Enum

class ChangeMode(Enum):
    ALL = 0
    NEW_ONLY = 1
    CHANGE_ONLY = 2


class ChangeModeCmd(Enum):
    ALL = 'git ls-files --modified && git ls-files --others --exclude-standar'
    NEW_ONLY = 'git ls-files --others --exclude-standar'
    CHANGE_ONLY = 'git ls-files --modified'

    def __str__(self):
        return str(self.value)


def elapsed_time(start:float):
    return time.time() - start

def get_changed_files(path=".", cmd=None, mode:ChangeMode=ChangeMode.ALL):
    import subprocess
    cd = 'cd {}'.format(path)
    if cmd is None:
        if mode == ChangeMode.ALL:
            cmd = str(ChangeModeCmd.ALL)
        elif mode == ChangeMode.NEW_ONLY:
            cmd = str(ChangeModeCmd.NEW_ONLY)
        elif mode == ChangeMode.CHANGE_ONLY:
            cmd = str(ChangeModeCmd.CHANGE_ONLY)
    s = subprocess.getstatusoutput('{} && {}'.format(cd, cmd))
    return s[1]

def open_ftp(hostname='localhost', username='root', password=None):
    connecting_str = 'connecting to {} as {} ...'.format(hostname,username)
    print(connecting_str, end='\r')
    session = ftplib.FTP(hostname,username,password)
    print('connected!'.ljust(len(connecting_str), ' '))
    return session

def chdir(session: ftplib.FTP, dir, debug=False): 
    if debug:
        print("chdir: {}".format(dir))
    if dir != os.sep and directory_exists(session, dir) is False: # (or negate, whatever you prefer for readability)
        session.mkd(dir)
    session.cwd(dir)

def chdir_nested(session: ftplib.FTP, dir, debug=False):
    path = os.path.normpath(dir)
    nested_dirs = path.split(os.sep)
    for dir in nested_dirs:
        chdir(session, dir)

def directory_exists(session: ftplib.FTP, dir):
    filelist = []
    session.retrlines('LIST',filelist.append)
    for f in filelist:
        if f.split()[-1] == dir and f.upper().startswith('D'):
            return True
    return False

def ftp_send_file(session: ftplib.FTP, file_path, base_dir=None, rename_to=None, debug=False):
    file = open(file_path,'rb')
    base_file_path, file_extension = os.path.splitext(file_path)
    filename = os.path.basename(base_file_path)
    if rename_to is not None:
        filename, rename_file_extension = os.path.splitext(rename_to)
        if len(rename_file_extension) > 0:
            file_extension = rename_file_extension
    if base_dir is not None:
        chdir_nested(session, base_dir, debug=debug)
    full_directory_path = os.path.dirname(file_path)
    path = os.path.normpath(full_directory_path)
    if path != filename:
        chdir_nested(session, path, debug=debug)
    if debug:
        print('STOR: {}{}'.format(filename, file_extension))
    session.storbinary(f'STOR {filename}{file_extension}', file)
    chdir(session, os.sep, debug=debug)
    file.close()    

def ftp_send_files(session: ftplib.FTP, file_paths=[], base_dir=None):
    start = time.time()
    current = 0
    n = 0
    for i in file_paths:
        n = progress_bar(current, len(file_paths), title=f'({current+1}/{len(file_paths)}) Uploading {i} ...')
        ftp_send_file(session, i, base_dir)
        current += 1
    upload_time = "{:.2f}".format(elapsed_time(start))
    progress_bar(current, len(file_paths), title=f'Completed in {upload_time} seconds!'.ljust(n, ' '))
    

def quit_ftp(session: ftplib.FTP):
    disconnecting_str = 'disconnecting...'
    print(disconnecting_str, end='\r')
    if session is not None:
        session.quit()
    print('disconnected!'.ljust(len(disconnecting_str), ' '))

def progress_bar(current, total, bar_length=20, title=None):
    fraction = current / total

    arrow = int(fraction * bar_length - 1) * '-' + '>'
    padding = int(bar_length - len(arrow)) * ' '

    str_title = ""
    if title is not None:
        str_title = f' {title}'

    ending = '\n' if current == total else '\r'
    progress_str = f'Progress: [{arrow}{padding}] {int(fraction*100)}%{str_title}'
    print(progress_str, end=ending)
    return len(progress_str)

def uploads(hostname, username, password, base_dir, file_paths=[]):
    ftp = open_ftp(hostname, username, password)
    try:
        ftp_send_files(ftp, file_paths, base_dir) 
    finally:
        if ftp is not None:
            quit_ftp(ftp)

if __name__ == "__main__":
    path = "."
    cmd = None
    ftp_hostname = ""
    ftp_username = ""
    ftp_password = ""
    ftp_basedir = ''
    for i in sys.argv:
        parts = i.split('=')
        opt = parts[0].removeprefix('--')
        if opt == 'path':
            path = parts[1]
        if opt == 'cmd':
            cmd = parts[1]
        if opt in ['host','hostname']:
            ftp_hostname = parts[1]
        if opt in ['user','username']:
            ftp_username = parts[1]
        if opt in ['pass','password']:
            ftp_password = parts[1]
        if opt in ['basedir']:
            ftp_basedir = parts[1]
    result = get_changed_files(path, cmd)
    uploads(ftp_hostname, ftp_username, ftp_password, ftp_basedir, result.split('\n'))