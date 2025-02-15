local apiUrl = "http://127.0.0.1:4000/api"

local function GetDiscordID(player)
    local discord = GetPlayerIdentifierByType(player, 'discord')
    if discord then
        local id = discord:gsub('discord:', '')
        return id
    end

    return nil
end

local function dbUpdate(endpoint, jsonData, callback)
    PerformHttpRequest(apiUrl .. endpoint, function(err, text, header)
        if err == 200 then
            callback(true, json.decode(text))
        else
            callback(false, nil)
        end
    end, 'POST', jsonData, { ["Content-Type"] = "application/json" })
end

function timeStart(player, type)
    if not player then
        print("ERROR: Time start export requires a player paramater")
        return
    end
    if not type then
        print("ERROR: Time start export requires a type paramater")
        return
    end
    local discordId = GetDiscordID(player)
    local jsonData = json.encode({ discordId = discordId, type = type})
    dbUpdate('/time/start', jsonData, function(success, data)
        if success then
            return
        else
            print("Time start failed")
        end
    end)
end

function timeEnd(player, type)
    if not player then
        print("ERROR: Time end export requires a player paramater")
        return
    end
    if not type then
        print("ERROR: Time end export requires a type paramater")
        return
    end
    local discordId = GetDiscordID(player)
    local jsonData = json.encode({ discordId = discordId, type = type})
    dbUpdate('/time/end', jsonData, function(success, data)
        if success then
            return
        else
            print("Time end failed")
        end
    end)
end