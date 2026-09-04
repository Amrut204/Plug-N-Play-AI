/**
 * Plug-N-Play AI Connector Middleware
 * 
 * Drop this single file into your Express project.
 * It creates a secure /schema and /execute endpoint that the 
 * Plug-N-Play AI platform uses to run safe, read-only queries.
 * 
 * No npm package needed — just this one file.
 */

import { Router } from 'express';
import crypto from 'crypto';

/**
 * Creates an Express router that acts as a secure bridge between
 * the Plug-N-Play AI platform and your database.
 * 
 * @param {Object} options
 * @param {string} options.sharedSecret - The HMAC secret key (same one you entered on the platform)
 * @param {Object} options.dbPool - Your database pool (pg Pool, mysql2 pool, or knex instance)
 * @param {string[]} options.tables - Array of table names the AI is allowed to query
 * @param {string} [options.dbType='postgres'] - 'postgres', 'mysql', or 'sqlite'
 * @returns {Router} Express router to mount at /api/v1/connector
 */
export function createConnectorRouter({ sharedSecret, dbPool, tables, dbType = 'postgres' }) {
  const router = Router();

  // --- HMAC Authentication Middleware ---
  function verifyHMAC(req, res, next) {
    const signature = req.headers['x-pnp-signature'];
    const timestamp = req.headers['x-pnp-timestamp'];

    if (!signature || !timestamp) {
      return res.status(401).json({ error: 'Missing authentication headers (x-pnp-signature, x-pnp-timestamp)' });
    }

    // Reject requests older than 5 minutes
    const age = Math.abs(Date.now() / 1000 - parseInt(timestamp));
    if (age > 300) {
      return res.status(401).json({ error: 'Request timestamp too old. Possible replay attack.' });
    }

    const payload = `${req.method}:${req.originalUrl}:${timestamp}`;
    const expected = crypto.createHmac('sha256', sharedSecret).update(payload).digest('hex');

    if (!crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected))) {
      return res.status(401).json({ error: 'Invalid HMAC signature. Check your shared secret key.' });
    }

    next();
  }

  // --- GET /schema - Returns the list of allowed tables and their columns ---
  router.get('/schema', verifyHMAC, async (req, res) => {
    try {
      const tableSchemas = [];

      for (const tableName of tables) {
        let columns = [];

        if (dbType === 'postgres') {
          const result = await dbPool.query(
            `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = $1 ORDER BY ordinal_position`,
            [tableName]
          );
          columns = result.rows.map(r => ({
            column_name: r.column_name,
            data_type: r.data_type
          }));
        } else if (dbType === 'mysql') {
          const [rows] = await dbPool.query(
            `SELECT COLUMN_NAME as column_name, DATA_TYPE as data_type FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ?`,
            [tableName]
          );
          columns = rows;
        }

        tableSchemas.push({
          table_name: tableName,
          business_name: tableName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
          description: `Data from the ${tableName} table`,
          columns
        });
      }

      res.json({ tables: tableSchemas });
    } catch (err) {
      console.error('[PnP Connector] Schema fetch error:', err.message);
      res.status(500).json({ error: 'Failed to fetch schema: ' + err.message });
    }
  });

  // --- POST /execute - Runs a safe, read-only SQL query ---
  router.post('/execute', verifyHMAC, async (req, res) => {
    const { sql, params } = req.body;

    if (!sql) {
      return res.status(400).json({ error: 'Missing "sql" in request body' });
    }

    // Safety: Only allow SELECT statements
    const normalized = sql.trim().toUpperCase();
    if (!normalized.startsWith('SELECT')) {
      return res.status(403).json({ error: 'Only SELECT queries are allowed. Blocked: ' + normalized.split(' ')[0] });
    }

    // Safety: Block dangerous keywords
    const blocked = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'TRUNCATE', 'GRANT', 'REVOKE'];
    for (const kw of blocked) {
      if (normalized.includes(kw)) {
        return res.status(403).json({ error: `Blocked dangerous keyword: ${kw}` });
      }
    }

    try {
      let rows;
      if (dbType === 'postgres') {
        const result = await dbPool.query(sql, params || []);
        rows = result.rows;
      } else if (dbType === 'mysql') {
        const [result] = await dbPool.query(sql, params || []);
        rows = result;
      }

      res.json({ rows, row_count: rows.length });
    } catch (err) {
      console.error('[PnP Connector] Query execution error:', err.message);
      res.status(500).json({ error: 'Query failed: ' + err.message });
    }
  });

  console.log(`[PnP Connector] ✅ Connector mounted! Whitelisted tables: [${tables.join(', ')}]`);
  return router;
}
