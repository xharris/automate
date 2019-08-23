import pexpect, sys, json

expect = {
    'eof': pexpect.EOF
}

import subprocess as sp
import os

no_sending = False
# username, host, port, password
class SSH():
    def __init__(self, username=None, host=None, port=None, password='', log=True):
        if not username:
            self.ssh_child = pexpect.spawn(username, encoding='utf-8', timeout=None)
        else:
            self.ssh_child = pexpect.spawn("ssh %s@%s -p %d"%(username,host,port), encoding='utf-8', timeout=None) #  -o StrictHostKeyChecking=no
        if log:
           self.ssh_child.logfile = sys.stdout
        self._expect = ""
        self.used_expect = False
        self.password = password

        if username != 'root':
            self.login(password)

    def log(self, yes):
        if yes:
            self.ssh_child.logfile = sys.stdout
        else:
            self.ssh_child.logfile = None

    def login(self,password):
        ret = self.expect(["assword: ","yes\\/no.*\\s"])
        if ret == 0:
            self.send(password)
        if ret == 1:
            self.send("yes")
            self.expect("assword: ")
            self.send(password)
        
    def yesno(self,yes=True):
        while self.expect(["yes[\\/\\\]no.*",pexpect.EOF,pexpect.TIMEOUT], timeout=5) == 0:
            if yes:
                self.send("yes")
            else:
                self.send("no")

    def expect(self,expect, timeout=-1):
        if not no_sending:
            self.used_expect = True
            self._expect = expect
            return self.ssh_child.expect(expect, timeout)

    def real_expect(self, expect):
        self.ssh_child.expect(expect)

    def send(self,line):
        if no_sending:
            print(line)
        else:
            if not self.used_expect:
                self.ssh_child.expect(self._expect)
            self.used_expect = False
            self.ssh_child.sendline(line)

    def output(self,expect):
        self.ssh_child.expect(self.expect)
        return self.ssh_child.before

    def readline(self):
        return self.ssh_child.readline()

    def close(self):
        if not self.used_expect:
            self.ssh_child.expect(self._expect)
        self.ssh_child.close()

    @staticmethod 
    def scp(in_file, out_file, user, address, port, password=''):
        sp_child = pexpect.spawn('scp -P %d %s %s@%s:%s'%(port,in_file,user,address,out_file), encoding='utf-8', logfile=sys.stdout)
        #sp_child.logfile_send = sys.stdout
        i = sp_child.expect(['assword: ',pexpect.EOF])
        if i == 0:
            sp_child.sendline(password)
            sp_child.expect(pexpect.EOF)
        sp_child.close()

class FnHelper():
    def __init__(self, parent):
        self.__parent = parent
    def output(self):
        return self.__parent.output
    def doInstruction(self, instr):
        self.__parent.doInstruction(instr)
    def get(self, var):
        if var in self.__parent.store:
            return self.__parent.store[var]
    def store(self, var, val):
        self.__parent.store[var] = val

class Automator():
    def __init__ (self):
        self.child = None
        self.ssh_configs = {}
        self.store = {}
        self.output = []

    def doInstruction (self, instr):
        instr_to_fn = {
            'ssh_config':self.ssh_config,
            'local_cmd':self.local_cmd,
            'ssh_cmd':self.ssh_cmd
        }
        fn = instr_to_fn.get(instr['type'], lambda args: "Invalid instruction type")
        if not 'skip' in instr or instr['skip'] != True:
            fn(instr)

    def ssh_config (self, args):
        name = args['name'] or '_default'
        self.ssh_configs[name] = args
        print("[%s] <- %s@%s:%s %s"%(args['name'], args['user'], args['host'], args['port'], '(w/ pass)' if args['pass'] else ''))

    def local_cmd (self, args):
        if self.child:
            self.child.close()
        self.cmd(args, 'local')

    def ssh_cmd (self, args):
        name = args['name'] or '_default'
        if self.child:
            self.child.close()
        if name in self.ssh_configs:
            ssh_args = self.ssh_configs[name]
            self.child = SSH(ssh_args['user'], ssh_args['host'], ssh_args['port'], ssh_args['pass'], log=('log' in args and args['log'] == True))
            self.child.name = name
            self.cmd(args, self.child)
        else:
            sys.exit("Error: no ssh config for '%s'"%(name))

    def close (self):
        if self.child:
            self.child.close()

    def cmd (self, args, child):
        local = (child == 'local')
        header = '[%s]'%('local' if local else child.name)
        self.output = []
        for line_info in args['lines']:
            if 'cmd' in line_info:
                line = line_info['cmd']
                replacements = {
                    '~': (os.path.expanduser('~') if local else '~')
                }
                # make all replacements
                for old, new in replacements.items():
                    line = line.replace(old, new)
                # gather stored variables user wants to use
                if 'args' in line_info:
                    store = [self.store[k] if k in self.store else sys.exit("Error: arg '{}' not found!".format(k)) for k in line_info['args']]
                    line = line.format(*store)
                print('%s %s'%(header, line))

                # save output
                if local:
                    self.output.append(pexpect.run(line))
                else:
                    child.send(line)
                    self.output.append(child.ssh_child.readline())

            if 'expect' in line_info and not local:
                child.expect(line_info['expect'])

            if 'pass' in line_info and not local:
                print("%s <= password"%(header))
                child.expect(line_info['pass'])
                child.send(child.password)

            if 'store' in line_info:
                val = ''
                if local:
                    val = self.output[-1]
                else:
                    val = child.readline()

                if 'args' in line_info:
                    if 'strip' in line_info['args']:
                        val = val.strip()
                if 'decode' in line_info:
                    val = val.decode(line_info['decode'])

                self.store[line_info['store']] = val
                print('%s -> (%s)'%(header, line_info['store']))

            if 'fn' in line_info:
                line_info['fn'](FnHelper(self))

            if 'yesno' in line_info:
                print("%s %s"%(header, "YES/no" if line_info['yesno'] else "yes/NO"))
                child.yesno(line_info['yesno'] == True)

            if 'log' in line_info:
                child.log(line_info['log'])

import importlib.util

if len(sys.argv) > 1:
    for p in sys.argv[1:]:
        spec = importlib.util.spec_from_file_location("module.name", p)
        script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(script)
        
        if script.instructions:
            auto = Automator()
            for i, instr in enumerate(script.instructions):
                auto.doInstruction(instr)
            auto.close()
