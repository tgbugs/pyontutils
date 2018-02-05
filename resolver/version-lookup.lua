local http = require 'resty.http'
local json = require 'json'
local user = 'SciCrunch'
local repo = 'NIF-Ontology'
local author_date_iso8601 = os.date('%Y-%m-%dT%H:%M:%S%z', ngx.var[3])
local furl = 'https://api.github.com/search/commits?q=repo:%s/%s+author-date:<=%s&sort=author-date&per_page=1'
local url = string.format(furl, user, repo, author_date_iso8601)
-- print(url)
local httpc = http.new()
local res, err = httpc:request_uri(url, {
		method = 'GET',
		headers = {
				['Accept'] = 'application/vnd.github.cloak-preview',
		}
})
local api_resp = json.parse(res.body)
if api_resp['items'] then
	local commit_sha = api_resp['items'][1]['sha']
	local fredirect = 'https://github.com/SciCrunch/NIF-Ontology/blob/%s%s/%s.ttl?raw=true'
	local rurl = string.format(fredirect, commit_sha, ngx.var[1], ngx.var[2])
	-- ngx.say(rurl)
	return ngx.redirect(rurl, ngx.HTTP_MOVED_TEMPORARILY)
else
	ngx.exit(ngx.HTTP_NOT_FOUND)
end
