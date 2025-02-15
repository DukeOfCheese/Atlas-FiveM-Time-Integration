game 'gta5'
fx_version 'cerulean'
lua54 'yes'

name 'Atlas Time Logger'
author 'DukeOfCheese@Atlas Development'
description 'Export resource that handles time logging in a database / Discord bot format'
version '1.0'

server_scripts {
    'server/server.lua'
}

server_exports {
    'timeStart',
    'timeEnd'
}