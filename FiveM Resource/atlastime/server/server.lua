local apiUrl = "http://127.0.0.1:5000/api"

local function GetDiscordID(player)
    local discord = GetPlayerIdentifierByType(player, 'discord')
    if discord then
        local id = discord:gsub('discord:', '')
        return id
    end

    return nil
end

local function PrintDebug(msg)
    if Config.Debug then
        print("[DEBUG] " .. msg)
    end
end

local function dataValidation(data)
    if not data.name then
        return false
    elseif not data.type then
        return false
    else
        return true
    end
end

local function dbUpdate(endpoint, data, callback)
    PerformHttpRequest(apiUrl .. endpoint, function(err, text, header)
        local data = json.decode(text)
        if err == 200 then
            callback(true)
        else
            callback(false)
        end
    end)
end

function timeStart(player, data)
    local discordId = GetDiscordID(player)
    if discordId then
        dbUpdate('/time/start', data, function(result)
            local response = result
            if not response then
                PrintDebug("Time start API failed for " .. player)
            end
        end)
    else
        PrintDebug("No Discord linked to " .. player)
    end
end

function timeEnd(player, data)
    local discordId = GetDiscordID(player)
    if discordId then
        dbUpdate('/time/end', data, function(result)
            local response = result
            if not response then
                PrintDebug("Time end API failed for " .. player)
            end
        end)
    else
        PrintDebug("No Discord linked to " .. player)
    end
end