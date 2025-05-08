local apiUrl = 'http://127.0.0.1:5000/api'
local apiPasskey = 'changeMe'
local headers = {
    ['Content-Type'] = 'application/json',
}

local function GetDiscordID(player)
    local discordId = Player(player).state.discordId
    if discordId ~= 0 then
        return discordId
    else
        local discord = GetPlayerIdentifierByType(player, 'discord')
        if discord then
            local id = discord:gsub('discord:', '')
            Player(player).state.discordId = id
            return id
        end
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

local function dbRequest(endpoint, method, data)
    local statusCode, responseBody, responseHeaders, errorData = PerformHttpRequestAwait(apiUrl .. endpoint, method, data, headers)
    local data = json.decode(text)
    if err == 200 then
        return true
    else
        return false
    end
end

function timeStart(player, data)
    local discordId = GetDiscordID(player)
    if discordId then
        if dataValidation(data) then
            local response = dbRequest('/time/start', 'POST', data)
            if not response then
                PrintDebug('timeStart API failed for ' .. player)
            else
                PrintDebug('timeStart API success for ' .. player)
            end
        else
            PrintDebug('Data passed was malformed for timeStart')
        end
    else
        PrintDebug('No Discord linked to ' .. player .. ' for timeStart')
    end
end

function timeEnd(player, data)
    local discordId = GetDiscordID(player)
    if discordId then
        if dataValidation(data) then
            local response = dbRequest('/time/end', 'POST', data)
            if not response then
                PrintDebug('timeEnd API failed for ' .. player)
            else
                PrintDebug('timeEnd API success for ' .. player)
            end
        else
            PrintDebug('Data passed was malformed for timeEnd')
        end
    else
        PrintDebug('No Discord linked to ' .. player .. ' for timeEnd')
    end
end