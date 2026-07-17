#!/usr/bin/env node
/**
 * GHL MCP client via openclaw-gateway network path (Cloudflare-safe).
 */
const fs = require("fs");

const pit = process.env.GHL_PIT || "";
const locationId = process.env.GHL_LOCATION_ID || "";
const outFile = process.env.GHL_MCP_OUTFILE || "";
const compactLimit = parseInt(process.env.GHL_COMPACT_LIMIT || "500", 10) || 500;
const MCP_URL = "https://services.leadconnectorhq.com/mcp/";

if (!pit || !locationId) {
  console.error(JSON.stringify({ error: "GHL_PIT and GHL_LOCATION_ID required" }));
  process.exit(1);
}

const headers = {
  Authorization: `Bearer ${pit}`,
  locationId,
  "Content-Type": "application/json",
  Accept: "application/json, text/event-stream",
};

function parseBody(text) {
  const trimmed = (text || "").trim();
  if (!trimmed) return null;
  if (trimmed.startsWith("{")) {
    try {
      return JSON.parse(trimmed);
    } catch {
      /* fall through */
    }
  }
  for (const line of trimmed.split("\n")) {
    if (line.startsWith("data:")) {
      const payload = line.slice(5).trim();
      if (!payload) continue;
      try {
        return JSON.parse(payload);
      } catch {
        /* continue */
      }
    }
  }
  return { raw: trimmed.slice(0, 4000) };
}

function parseEmbeddedJson(text) {
  if (!text || typeof text !== "string") return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function compactToolResult(result) {
  const content = result?.content;
  if (!Array.isArray(content) || !content[0]?.text) return result;
  const embedded = parseEmbeddedJson(content[0].text);
  if (!embedded || typeof embedded !== "object") {
    return { preview: String(content[0].text).slice(0, 2000) };
  }
  const data = embedded.data || embedded;
  const out = { success: embedded.success, status: embedded.status };
  if (Array.isArray(data.contacts)) {
    out.contacts = data.contacts.slice(0, compactLimit).map((c) => ({
      id: c.id,
      contactName: c.contactName || c.name,
      firstName: c.firstName,
      lastName: c.lastName,
      email: c.email,
      phone: c.phone,
      tags: c.tags,
      source: c.source,
      dateAdded: c.dateAdded || c.createdAt || c.dateCreated,
      lastActivity: c.lastActivity || c.dateUpdated || c.updatedAt,
      customFields: c.customFields || c.customField,
      assignedTo: c.assignedTo,
      dnd: c.dnd,
    }));
    out.totalContacts = out.contacts.length;
    out.meta = data.meta || embedded.meta;
  }
  if (Array.isArray(data.pipelines)) {
    out.pipelines = data.pipelines.map((p) => ({
      id: p.id,
      name: p.name,
      stages: Array.isArray(p.stages)
        ? p.stages.map((s) => ({ id: s.id, name: s.name, position: s.position }))
        : [],
    }));
  }
  if (Array.isArray(data.opportunities)) {
    out.opportunities = data.opportunities.slice(0, compactLimit).map((o) => ({
      id: o.id,
      name: o.name,
      status: o.status,
      pipelineId: o.pipelineId,
      pipelineStageId: o.pipelineStageId,
      contactId: o.contactId,
      monetaryValue: o.monetaryValue,
      updatedAt: o.updatedAt || o.dateUpdated,
      createdAt: o.createdAt || o.dateAdded,
    }));
  }
  if (Array.isArray(data.conversations)) {
    out.conversations = data.conversations.slice(0, compactLimit).map((c) => ({
      id: c.id,
      contactId: c.contactId,
      contactName: c.contactName,
      type: c.type,
      lastMessageType: c.lastMessageType,
      lastMessageDate: c.lastMessageDate,
      lastMessageBody: c.lastMessageBody,
      unreadCount: c.unreadCount,
      inbox: c.inbox,
    }));
  }
  if (Array.isArray(data.messages)) {
    out.messages = data.messages.slice(0, compactLimit).map((m) => ({
      id: m.id,
      direction: m.direction,
      type: m.messageType || m.type,
      body: String(m.body || m.message || m.content || "").slice(0, 4000),
      dateAdded: m.dateAdded || m.createdAt || m.timestamp,
      status: m.status,
      attachments: m.attachments,
      meta: m.meta,
    }));
  }
  if (data.contact && typeof data.contact === "object") {
    const c = data.contact;
    out.contact = {
      id: c.id,
      contactName: c.contactName || c.name,
      email: c.email,
      phone: c.phone,
      tags: c.tags,
      dateAdded: c.dateAdded || c.createdAt,
      lastActivity: c.lastActivity || c.dateUpdated,
      customFields: c.customFields || c.customField,
    };
  }
  if (data.location || data.name) {
    out.location = {
      id: data.id || data.location?.id,
      name: data.name || data.location?.name,
    };
  }
  if (Array.isArray(data.customFields)) {
    out.customFields = data.customFields.map((f) => ({
      id: f.id,
      name: f.name,
      fieldKey: f.fieldKey,
    }));
  }
  return out;
}

async function postJson(body) {
  const res = await fetch(MCP_URL, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  const text = await res.text();
  const parsed = parseBody(text);
  return { ok: res.ok, status: res.status, parsed };
}

async function initialize() {
  return postJson({
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: {
      protocolVersion: "2024-11-05",
      capabilities: {},
      clientInfo: { name: "clawsum-ghl-audit", version: "1.0" },
    },
  });
}

async function toolsList() {
  const init = await initialize();
  if (!init.ok) return init;
  return postJson({ jsonrpc: "2.0", id: 2, method: "tools/list", params: {} });
}

async function callTool(name, input) {
  const init = await initialize();
  if (!init.ok) return init;
  let res = await postJson({
    jsonrpc: "2.0",
    id: 3,
    method: "tools/call",
    params: { name, arguments: input || {} },
  });
  if (res.ok && res.parsed && !res.parsed.error) return res;
  return postJson({ tool: name, input: input || {} });
}

function emit(out) {
  const payload = JSON.stringify(out);
  if (outFile) {
    fs.writeFileSync(outFile, payload, "utf8");
    console.log(JSON.stringify({ ok: out.ok, status: out.status, outfile: outFile, toolCount: out.toolCount }));
  } else {
    console.log(payload.slice(0, 120000));
  }
}

async function main() {
  const cmd = process.argv[2] || "tools/list";
  let out;
  if (cmd === "tools/list") {
    out = await toolsList();
    const tools = out?.parsed?.result?.tools;
    if (Array.isArray(tools)) {
      out.toolNames = tools.map((t) => t.name).filter(Boolean);
      out.toolCount = out.toolNames.length;
      delete out.parsed.result.tools;
    }
  } else if (cmd === "call") {
    const name = process.argv[3];
    const raw = process.argv[4] || "{}";
    let input = {};
    try {
      input = JSON.parse(raw);
    } catch (e) {
      console.error(JSON.stringify({ error: "invalid JSON input", detail: String(e) }));
      process.exit(1);
    }
    if (!name) {
      console.error(JSON.stringify({ error: "tool name required" }));
      process.exit(1);
    }
    out = await callTool(name, input);
    if (out?.parsed?.result) {
      out.compact = compactToolResult(out.parsed.result);
    }
  } else {
    console.error(JSON.stringify({ error: "unknown command", cmd }));
    process.exit(1);
  }
  emit(out);
  process.exit(out.ok ? 0 : 1);
}

main().catch((e) => {
  console.error(JSON.stringify({ error: String(e) }));
  process.exit(1);
});
