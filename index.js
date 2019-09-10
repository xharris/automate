const nwSSH = require('ssh2-client');

class SSH {
    constructor (args) {
        this.ssh = nwSSH.shell(`${args.user ? args.user+'@' : ''}${host}`)
    }
}

