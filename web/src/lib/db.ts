import { createClient, type Client, type ResultSet, type InValue } from "@libsql/client";

// ---------------------------------------------------------------------------
// Singleton client
// ---------------------------------------------------------------------------

let _client: Client | null = null;

function getClient(): Client {
  if (!_client) {
    _client = createClient({
      url: process.env.TURSO_DATABASE_URL!,
      authToken: process.env.TURSO_AUTH_TOKEN,
    });
  }
  return _client;
}

// ---------------------------------------------------------------------------
// One-time init: ensure instructions table exists
// ---------------------------------------------------------------------------

let _initialized = false;

async function ensureInit(): Promise<Client> {
  const client = getClient();
  if (!_initialized) {
    await client.execute(`CREATE TABLE IF NOT EXISTS instructions (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL DEFAULT '',
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )`);
    await client.execute(
      "INSERT OR IGNORE INTO instructions (key, value) VALUES ('global', '')"
    );
    _initialized = true;
  }
  return client;
}

export { ensureInit };

// ---------------------------------------------------------------------------
// Row → plain object helpers
// ---------------------------------------------------------------------------

function rowToObject(
  row: ResultSet["rows"][number],
  columns: string[]
): Record<string, unknown> {
  const obj: Record<string, unknown> = {};
  columns.forEach((col, i) => {
    obj[col] = row[i];
  });
  return obj;
}

function memoryToDict(
  row: Record<string, unknown>,
  tags: string[]
): Record<string, unknown> {
  return {
    id: row.id,
    short_id: (row.id as string).slice(0, 8),
    project_id: row.project_id,
    content: row.content,
    depth: row.depth,
    source: row.source,
    superseded_by: row.superseded_by,
    category: row.category ?? "status",
    parent_memory_id: row.parent_memory_id ?? null,
    title: row.title ?? null,
    resolved: Boolean(row.resolved),
    created_at: row.created_at,
    updated_at: row.updated_at,
    tags,
  };
}

// Batch-fetch tags for a list of memory IDs.
// Returns a Map<memoryId, string[]>
async function fetchTagsForMemories(
  client: Client,
  memoryIds: string[]
): Promise<Map<string, string[]>> {
  const tagMap = new Map<string, string[]>();
  if (memoryIds.length === 0) return tagMap;

  const placeholders = memoryIds.map(() => "?").join(", ");
  const tagResult = await client.execute({
    sql: `SELECT memory_id, tag FROM memory_tags WHERE memory_id IN (${placeholders}) ORDER BY tag`,
    args: memoryIds,
  });

  for (const row of tagResult.rows) {
    const mid = row[0] as string;
    const tag = row[1] as string;
    if (!tagMap.has(mid)) tagMap.set(mid, []);
    tagMap.get(mid)!.push(tag);
  }

  return tagMap;
}

// ---------------------------------------------------------------------------
// Prefix-matching helper for memory IDs
// ---------------------------------------------------------------------------

async function resolveMemoryId(
  client: Client,
  id: string
): Promise<string | null> {
  // Try exact match first
  const exact = await client.execute({
    sql: "SELECT id FROM memories WHERE id = ?",
    args: [id],
  });
  if (exact.rows.length === 1) return exact.rows[0][0] as string;

  // Prefix match — escape LIKE special chars
  const escaped = id.replace(/\\/g, "\\\\").replace(/%/g, "\\%").replace(/_/g, "\\_");
  const prefix = await client.execute({
    sql: "SELECT id FROM memories WHERE id LIKE ? ESCAPE '\\'",
    args: [escaped + "%"],
  });
  if (prefix.rows.length === 1) return prefix.rows[0][0] as string;

  return null;
}

// ---------------------------------------------------------------------------
// 1. listProjects
// ---------------------------------------------------------------------------

export async function listProjects(
  status?: string
): Promise<Record<string, unknown>[]> {
  const client = await ensureInit();

  const sql = status
    ? `SELECT p.*, (SELECT COUNT(*) FROM memories m WHERE m.project_id = p.id AND m.superseded_by IS NULL) AS memory_count
       FROM projects p WHERE p.status = ? ORDER BY p.updated_at DESC`
    : `SELECT p.*, (SELECT COUNT(*) FROM memories m WHERE m.project_id = p.id AND m.superseded_by IS NULL) AS memory_count
       FROM projects p ORDER BY p.updated_at DESC`;

  const args = status ? [status] : [];
  const result = await client.execute({ sql, args });

  return result.rows.map((row) => rowToObject(row, result.columns));
}

// ---------------------------------------------------------------------------
// 2. getProject
// ---------------------------------------------------------------------------

export async function getProject(
  id: string
): Promise<Record<string, unknown> | null> {
  const client = await ensureInit();

  const projResult = await client.execute({
    sql: "SELECT * FROM projects WHERE id = ?",
    args: [id],
  });
  if (projResult.rows.length === 0) return null;

  const project = rowToObject(projResult.rows[0], projResult.columns);

  const countResult = await client.execute({
    sql: "SELECT COUNT(*) AS cnt FROM memories WHERE project_id = ? AND superseded_by IS NULL",
    args: [id],
  });
  project.memory_count = countResult.rows[0][0] as number;

  return project;
}

// ---------------------------------------------------------------------------
// 3. createProject
// ---------------------------------------------------------------------------

export async function createProject(data: {
  id: string;
  name: string;
  summary?: string | null;
  github_repo?: string | null;
  category?: string;
}): Promise<Record<string, unknown>> {
  const client = await ensureInit();

  const now = new Date().toISOString();
  const category = data.category ?? "project";

  await client.execute({
    sql: `INSERT INTO projects (id, name, summary, github_repo, category, created_at, updated_at)
          VALUES (?, ?, ?, ?, ?, ?, ?)`,
    args: [
      data.id,
      data.name,
      data.summary ?? null,
      data.github_repo ?? null,
      category,
      now,
      now,
    ],
  });

  const created = await getProject(data.id);
  if (!created) throw new Error(`Failed to retrieve created project ${data.id}`);
  return created;
}

// ---------------------------------------------------------------------------
// 4. updateProject
// ---------------------------------------------------------------------------

export async function updateProject(
  id: string,
  data: Partial<{
    name: string;
    status: string;
    summary: string | null;
    github_repo: string | null;
    category: string;
  }>
): Promise<Record<string, unknown>> {
  const client = await ensureInit();

  // If summary is being updated, save old summary to revisions table
  if ("summary" in data) {
    const existing = await getProject(id);
    if (existing && existing.summary != null) {
      await client.execute({
        sql: "INSERT INTO project_summary_revisions (project_id, summary) VALUES (?, ?)",
        args: [id, existing.summary as string],
      });
      await client.execute({
        sql: `DELETE FROM project_summary_revisions
              WHERE project_id = ? AND id NOT IN (
                SELECT id FROM project_summary_revisions
                WHERE project_id = ?
                ORDER BY created_at DESC LIMIT 10
              )`,
        args: [id, id],
      });
    }
  }

  const now = new Date().toISOString();
  const fields: string[] = [];
  const args: InValue[] = [];

  if ("name" in data) {
    fields.push("name = ?");
    args.push(data.name ?? null);
  }
  if ("status" in data) {
    fields.push("status = ?");
    args.push(data.status ?? null);
  }
  if ("summary" in data) {
    fields.push("summary = ?");
    args.push(data.summary ?? null);
  }
  if ("github_repo" in data) {
    fields.push("github_repo = ?");
    args.push(data.github_repo ?? null);
  }
  if ("category" in data) {
    fields.push("category = ?");
    args.push(data.category ?? null);
  }

  fields.push("updated_at = ?");
  args.push(now);
  args.push(id);

  const result = await client.execute({
    sql: `UPDATE projects SET ${fields.join(", ")} WHERE id = ?`,
    args,
  });

  if (result.rowsAffected === 0) {
    throw new Error(`Project not found: ${id}`);
  }

  const updated = await getProject(id);
  if (!updated) throw new Error(`Failed to retrieve updated project ${id}`);
  return updated;
}

// ---------------------------------------------------------------------------
// 4b. deleteProject
// ---------------------------------------------------------------------------

export async function deleteProject(id: string): Promise<boolean> {
  const client = await ensureInit();

  // Check project exists
  const check = await client.execute({
    sql: "SELECT id FROM projects WHERE id = ?",
    args: [id],
  });
  if (check.rows.length === 0) return false;

  // Cascade delete: tags → memories → revisions → project
  await client.execute({
    sql: "DELETE FROM memory_tags WHERE memory_id IN (SELECT id FROM memories WHERE project_id = ?)",
    args: [id],
  });
  await client.execute({
    sql: "DELETE FROM memories WHERE project_id = ?",
    args: [id],
  });
  await client.execute({
    sql: "DELETE FROM project_summary_revisions WHERE project_id = ?",
    args: [id],
  });
  await client.execute({
    sql: "DELETE FROM projects WHERE id = ?",
    args: [id],
  });

  return true;
}

// ---------------------------------------------------------------------------
// 5. getSummaryRevision
// ---------------------------------------------------------------------------

export async function getSummaryRevision(
  projectId: string
): Promise<{ previous_summary: string; updated_at: string }[]> {
  const client = await ensureInit();

  const result = await client.execute({
    sql: `SELECT summary, created_at FROM project_summary_revisions
          WHERE project_id = ? ORDER BY created_at DESC LIMIT 10`,
    args: [projectId],
  });

  return result.rows.map((row) => ({
    previous_summary: row[0] as string,
    updated_at: row[1] as string,
  }));
}

// ---------------------------------------------------------------------------
// 6. clearSummaryRevision
// ---------------------------------------------------------------------------

export async function clearSummaryRevision(projectId: string): Promise<void> {
  const client = await ensureInit();
  await client.execute({
    sql: "DELETE FROM project_summary_revisions WHERE project_id = ?",
    args: [projectId],
  });
}

// ---------------------------------------------------------------------------
// 7. listMemories (recall)
// ---------------------------------------------------------------------------

export async function listMemories(
  projectId: string,
  maxChars?: number,
  tags?: string[]
): Promise<{
  memories: Record<string, unknown>[];
  stats: {
    chars_loaded: number;
    chars_budget: number;
    memories_loaded: number;
    memories_dropped: number;
  };
}> {
  const client = await ensureInit();

  let whereClause = `project_id = ? AND superseded_by IS NULL`;
  const args: InValue[] = [projectId];

  if (tags && tags.length > 0) {
    for (const tag of tags) {
      whereClause += ` AND id IN (SELECT memory_id FROM memory_tags WHERE tag = ?)`;
      args.push(tag);
    }
  }

  const countResult = await client.execute({
    sql: `SELECT COUNT(*) AS cnt FROM memories WHERE ${whereClause}`,
    args,
  });
  const totalMatching = Number(countResult.rows[0]?.[0] ?? 0);

  const sql = `SELECT * FROM memories
    WHERE ${whereClause}
    ORDER BY updated_at DESC
    LIMIT 50`;

  const result = await client.execute({ sql, args });
  const rows = result.rows.map((row) => rowToObject(row, result.columns));

  // Batch-fetch tags
  const memoryIds = rows.map((r) => r.id as string);
  const tagMap = await fetchTagsForMemories(client, memoryIds);

  // Apply character budget
  const budget = maxChars ?? Infinity;
  let charsLoaded = 0;
  let memoriesLoaded = 0;
  const memories: Record<string, unknown>[] = [];

  for (const row of rows) {
    const content = (row.content as string) ?? "";
    const charCount = content.length;
    if (charsLoaded + charCount > budget) {
      break;
    }
    charsLoaded += charCount;
    memoriesLoaded++;
    const rowTags = tagMap.get(row.id as string) ?? [];
    memories.push(memoryToDict(row, rowTags));
  }

  const memoriesDropped = Math.max(totalMatching - memoriesLoaded, 0);

  return {
    memories,
    stats: {
      chars_loaded: charsLoaded,
      chars_budget: maxChars ?? -1,
      memories_loaded: memoriesLoaded,
      memories_dropped: memoriesDropped,
    },
  };
}

// ---------------------------------------------------------------------------
// 8. getMemory (with prefix matching)
// ---------------------------------------------------------------------------

export async function getMemory(
  id: string
): Promise<Record<string, unknown> | null> {
  const client = await ensureInit();

  const resolvedId = await resolveMemoryId(client, id);
  if (!resolvedId) return null;

  const result = await client.execute({
    sql: "SELECT * FROM memories WHERE id = ?",
    args: [resolvedId],
  });
  if (result.rows.length === 0) return null;

  const row = rowToObject(result.rows[0], result.columns);
  const tagMap = await fetchTagsForMemories(client, [resolvedId]);
  const tags = tagMap.get(resolvedId) ?? [];

  return memoryToDict(row, tags);
}

// ---------------------------------------------------------------------------
// 9. createMemory
// ---------------------------------------------------------------------------

export async function createMemory(data: {
  project_id: string;
  content: string;
  source?: string;
  tags?: string[];
}): Promise<Record<string, unknown>> {
  const client = await ensureInit();

  const id = crypto.randomUUID().replace(/-/g, "");
  const source = data.source ?? "conversation";
  const now = new Date().toISOString();
  const tags = data.tags ?? [];

  await client.execute({
    sql: `INSERT INTO memories (id, project_id, content, depth, source, category, parent_memory_id, title, created_at, updated_at)
          VALUES (?, ?, ?, 1, ?, 'status', null, null, ?, ?)`,
    args: [id, data.project_id, data.content, source, now, now],
  });

  for (const tag of tags) {
    await client.execute({
      sql: "INSERT INTO memory_tags (memory_id, tag) VALUES (?, ?)",
      args: [id, tag],
    });
  }

  await client.execute({
    sql: "UPDATE projects SET updated_at = ? WHERE id = ?",
    args: [now, data.project_id],
  });

  const created = await getMemory(id);
  if (!created) throw new Error(`Failed to retrieve created memory ${id}`);
  return created;
}

// ---------------------------------------------------------------------------
// 10. updateMemory
// ---------------------------------------------------------------------------

export async function updateMemory(
  id: string,
  data: { content?: string; tags?: string[] }
): Promise<Record<string, unknown>> {
  const client = await ensureInit();

  const resolvedId = await resolveMemoryId(client, id);
  if (!resolvedId) throw new Error(`Memory not found: ${id}`);

  // Check it exists and is not superseded
  const check = await client.execute({
    sql: "SELECT id, project_id, superseded_by FROM memories WHERE id = ?",
    args: [resolvedId],
  });
  if (check.rows.length === 0) throw new Error(`Memory not found: ${resolvedId}`);
  const checkRow = rowToObject(check.rows[0], check.columns);
  if (checkRow.superseded_by != null) {
    throw new Error(`Memory ${resolvedId} is already superseded`);
  }

  const now = new Date().toISOString();
  const fields: string[] = [];
  const args: InValue[] = [];

  if ("content" in data && data.content !== undefined) {
    fields.push("content = ?");
    args.push(data.content);
  }

  fields.push("updated_at = ?");
  args.push(now);
  args.push(resolvedId);

  await client.execute({
    sql: `UPDATE memories SET ${fields.join(", ")} WHERE id = ?`,
    args,
  });

  if (data.tags !== undefined) {
    await client.execute({
      sql: "DELETE FROM memory_tags WHERE memory_id = ?",
      args: [resolvedId],
    });
    for (const tag of data.tags) {
      await client.execute({
        sql: "INSERT INTO memory_tags (memory_id, tag) VALUES (?, ?)",
        args: [resolvedId, tag],
      });
    }
  }

  // Bump project updated_at
  const projectId = checkRow.project_id as string;
  await client.execute({
    sql: "UPDATE projects SET updated_at = ? WHERE id = ?",
    args: [now, projectId],
  });

  const updated = await getMemory(resolvedId);
  if (!updated) throw new Error(`Failed to retrieve updated memory ${resolvedId}`);
  return updated;
}

// ---------------------------------------------------------------------------
// 11. deleteMemory (soft delete)
// ---------------------------------------------------------------------------

export async function deleteMemory(id: string): Promise<boolean> {
  const client = await ensureInit();

  const resolvedId = await resolveMemoryId(client, id);
  if (!resolvedId) return false;

  const now = new Date().toISOString();
  const result = await client.execute({
    sql: `UPDATE memories SET superseded_by = '_deleted', updated_at = ?
          WHERE id = ? AND superseded_by IS NULL`,
    args: [now, resolvedId],
  });

  return result.rowsAffected > 0;
}

// ---------------------------------------------------------------------------
// 12. getSupersedChain (recursive CTE traversal)
// ---------------------------------------------------------------------------

export async function getSupersedChain(
  memoryId: string
): Promise<Record<string, unknown>[]> {
  const client = await ensureInit();

  const resolvedId = await resolveMemoryId(client, memoryId);
  if (!resolvedId) return [];

  const chainResult = await client.execute({
    sql: `WITH RECURSIVE chain(id) AS (
            SELECT id FROM memories WHERE id = ?
            UNION
            SELECT m.id
            FROM memories m
            JOIN chain c ON m.superseded_by = c.id
            UNION
            SELECT m.superseded_by
            FROM memories m
            JOIN chain c ON m.id = c.id
            WHERE m.superseded_by IS NOT NULL
              AND m.superseded_by != '_deleted'
          )
          SELECT DISTINCT id FROM chain`,
    args: [resolvedId],
  });

  const ids = chainResult.rows.map((row) => row[0] as string);
  if (ids.length === 0) return [];

  const placeholders = ids.map(() => "?").join(", ");
  const result = await client.execute({
    sql: `SELECT * FROM memories WHERE id IN (${placeholders}) ORDER BY created_at ASC`,
    args: ids,
  });

  const rows = result.rows.map((row) => rowToObject(row, result.columns));
  const tagMap = await fetchTagsForMemories(client, ids);

  return rows.map((row) => memoryToDict(row, tagMap.get(row.id as string) ?? []));
}

// ---------------------------------------------------------------------------
// 13. searchMemories
// ---------------------------------------------------------------------------

export async function searchMemories(
  query: string,
  projectId?: string,
  tags?: string[],
  limit?: number
): Promise<Record<string, unknown>[]> {
  const client = await ensureInit();

  const safeQuery = '"' + query.replace(/"/g, '""') + '"';
  const maxLimit = limit ?? 50;

  let sql = `SELECT m.* FROM memories m
             JOIN memories_fts f ON m.rowid = f.rowid
             WHERE memories_fts MATCH ?
             AND m.superseded_by IS NULL`;
  const args: InValue[] = [safeQuery];

  if (projectId) {
    sql += " AND m.project_id = ?";
    args.push(projectId);
  }

  if (tags && tags.length > 0) {
    for (const tag of tags) {
      sql += " AND m.id IN (SELECT memory_id FROM memory_tags WHERE tag = ?)";
      args.push(tag);
    }
  }

  sql += " ORDER BY f.rank, m.updated_at DESC LIMIT ?";
  args.push(maxLimit);

  const result = await client.execute({ sql, args });
  const rows = result.rows.map((row) => rowToObject(row, result.columns));

  const memoryIds = rows.map((r) => r.id as string);
  const tagMap = await fetchTagsForMemories(client, memoryIds);

  return rows.map((row) => memoryToDict(row, tagMap.get(row.id as string) ?? []));
}

// ---------------------------------------------------------------------------
// 14. getAllTags
// ---------------------------------------------------------------------------

export async function getAllTags(projectId?: string): Promise<string[]> {
  const client = await ensureInit();

  const sql = projectId
    ? `SELECT DISTINCT mt.tag FROM memory_tags mt
       JOIN memories m ON mt.memory_id = m.id
       WHERE m.superseded_by IS NULL AND m.project_id = ?
       ORDER BY mt.tag`
    : `SELECT DISTINCT mt.tag FROM memory_tags mt
       JOIN memories m ON mt.memory_id = m.id
       WHERE m.superseded_by IS NULL
       ORDER BY mt.tag`;

  const args = projectId ? [projectId] : [];
  const result = await client.execute({ sql, args });

  return result.rows.map((row) => row[0] as string);
}

// ---------------------------------------------------------------------------
// 15. getDashboardStats
// ---------------------------------------------------------------------------

export async function getDashboardStats(): Promise<{
  total_projects: number;
  active_projects: number;
  total_memories: number;
  stale_projects: number;
}> {
  const client = await ensureInit();

  const [totalProj, activeProj, totalMem, staleProj] = await Promise.all([
    client.execute("SELECT COUNT(*) FROM projects"),
    client.execute("SELECT COUNT(*) FROM projects WHERE status = 'active'"),
    client.execute("SELECT COUNT(*) FROM memories WHERE superseded_by IS NULL"),
    client.execute(
      "SELECT COUNT(*) FROM projects WHERE status = 'active' AND updated_at < datetime('now', '-7 days')"
    ),
  ]);

  return {
    total_projects: totalProj.rows[0][0] as number,
    active_projects: activeProj.rows[0][0] as number,
    total_memories: totalMem.rows[0][0] as number,
    stale_projects: staleProj.rows[0][0] as number,
  };
}

// ---------------------------------------------------------------------------
// 16. getInstructions
// ---------------------------------------------------------------------------

export async function getInstructions(): Promise<string> {
  const client = await ensureInit();

  const result = await client.execute({
    sql: "SELECT value FROM instructions WHERE key = 'global'",
    args: [],
  });

  if (result.rows.length === 0) return "";
  return (result.rows[0][0] as string) ?? "";
}

// ---------------------------------------------------------------------------
// 17. putInstructions
// ---------------------------------------------------------------------------

export async function putInstructions(content: string): Promise<void> {
  const client = await ensureInit();

  await client.execute({
    sql: "UPDATE instructions SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = 'global'",
    args: [content],
  });
}
