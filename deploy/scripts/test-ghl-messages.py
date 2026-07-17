#!/usr/bin/env python3
import json, sys
sys.path.insert(0, "/docker/clawsum/scripts")
from ghl_mcp_client import load_env, mcp_tools_list, mcp_tool
import ghl_accounts as ghl

env = load_env()
acc = ghl.account_by_slug("ghl")
pit = env[acc["env_pit"]]
loc = env[acc["env_location"]]
avail, _ = mcp_tools_list(pit, loc)
convs = mcp_tool("conversations_search-conversation", {"limit": 3}, pit, loc, avail)
cid = convs["conversations"][0]["id"] if convs.get("conversations") else None
print("conv_id", cid)
if cid:
    for params in [{"conversationId": cid}, {"conversation_id": cid}, {"id": cid}]:
        r = mcp_tool("conversations_get-messages", params, pit, loc, avail)
        n = len(r.get("messages") or []) if isinstance(r, dict) else 0
        print(params, "messages", n, "keys", list(r.keys()) if isinstance(r, dict) else type(r))
