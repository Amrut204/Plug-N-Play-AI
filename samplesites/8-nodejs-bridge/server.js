// server.js — Node.js Zero-Knowledge Bridge Server
const express = require('express');
const path = require('path');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;
const PNP_HOST = process.env.PNP_HOST || 'https://plug-n-play-rag.onrender.com';
const AGENT_ID = process.env.PNP_AGENT_ID || 'YOUR_AGENT_ID';
const MASTER_KEY = process.env.PNP_MASTER_API_KEY || '';

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Simulated local private database records
const localPrivateDatabase = {
  orders: [
    { order_id: 'ORD-901', customer_name: 'John Doe', status: 'Delivered', total_amount: 349.99, delivery_days: 2 },
    { order_id: 'ORD-902', customer_name: 'Jane Smith', status: 'Processing', total_amount: 129.50, delivery_days: 3 },
    { order_id: 'ORD-903', customer_name: 'Alex Brown', status: 'Shipped', total_amount: 99.00, delivery_days: 1 }
  ]
};

// =========================================================================
// 📍 WHERE TO PLACE IN AN EXISTING PRODUCTION CODEBASE:
// If you already have an existing Express app with thousands of lines,
// you DO NOT replace your whole file! 
// Just copy only the route below (`app.post('/api/ai-chat', ...)`)
// and paste it into your existing routes file or server.js.
// =========================================================================
app.post('/api/ai-chat', async (req, res) => {
  const { query, userId, userRole } = req.body;

  if (!query) {
    return res.status(400).json({ error: 'Missing query parameter.' });
  }

  try {
    // Step 1: Ask Plug-N-Play to synthesize safe SQL from schema (Zero database access to cloud)
    const genRes = await fetch(`${PNP_HOST}/api/v1/chat/generate-sql`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        ...(MASTER_KEY ? { 'Authorization': `Bearer ${MASTER_KEY}` } : {})
      },
      body: JSON.stringify({
        agent_id: AGENT_ID,
        query,
        user_id: userId || 'guest',
        user_role: userRole || 'user'
      })
    });

    const genData = await genRes.json();

    // Guardrail blocked check
    if (genData.guardrail_blocked) {
      return res.json({ answer: genData.refusal_message, route: 'GUARDRAIL_BLOCKED' });
    }

    const sql = genData.sql_query || '';
    let dbRows = [];

    // Step 2: Execute locally on your private database (Inside your VPC/Firewall)
    if (sql) {
      console.log(`[Bridge Server] Executing local safe query: ${sql}`);
      // Query local private database
      dbRows = localPrivateDatabase.orders;
    }

    // Step 3: Send query results back to Plug-N-Play for natural language formatting
    const formatRes = await fetch(`${PNP_HOST}/api/v1/chat/format-sql-response`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agent_id: AGENT_ID,
        query,
        sql_query: sql,
        db_results: dbRows
      })
    });

    const formatData = await formatRes.json();
    return res.json({
      answer: formatData.answer || 'Query completed.',
      sql_executed: sql,
      local_rows_count: dbRows.length
    });

  } catch (err) {
    console.error('[Bridge Error]', err);
    return res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`🚀 Node.js Zero-Knowledge Bridge Server listening on http://localhost:${PORT}`);
});
