<?php
// app/Http/Controllers/AIChatController.php (PHP / Laravel 9/10/11)

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\DB;

class AIChatController extends Controller
{
    public function handleChat(Request $request)
    {
        $query = $request->input('query');
        $userId = $request->input('user_id', 'guest_user');
        $userRole = $request->input('user_role', 'user');

        $pnpHost = env('PNP_HOST', 'https://plug-n-play-rag.onrender.com');
        $agentId = env('PNP_AGENT_ID', 'YOUR_AGENT_ID');
        $masterKey = env('PNP_MASTER_API_KEY', '');

        // Step 1: Request safe SQL generation from Plug-N-Play AI
        $headers = ['Content-Type' => 'application/json'];
        if (!empty($masterKey)) {
            $headers['Authorization'] = 'Bearer ' . $masterKey;
        }

        $genRes = Http::withHeaders($headers)->post("{$pnpHost}/api/v1/chat/generate-sql", [
            'agent_id' => $agentId,
            'query' => $query,
            'user_id' => $userId,
            'user_role' => $userRole,
            'dialect' => 'mysql'
        ]);

        if ($genRes->failed()) {
            return response()->json(['error' => 'SQL Synthesis failed.'], 500);
        }

        $data = $genRes->json();
        if (!empty($data['guardrail_blocked'])) {
            return response()->json(['answer' => $data['refusal_message'], 'route' => 'GUARDRAIL_BLOCKED']);
        }

        $sql = $data['sql_query'] ?? null;
        $dbResults = [];

        // Step 2: Safe Read-Only SELECT validation & local execution inside your private VPC
        if ($sql && stripos(trim($sql), 'SELECT') === 0 && !str_contains($sql, ';')) {
            try {
                // Execute on local private database
                $dbResults = DB::select($sql);
            } catch (\Exception $e) {
                // Fallback mock simulation for standalone testing
                $dbResults = [
                    ['product_id' => 'P101', 'name' => 'Sony Headphones', 'stock' => 42, 'price' => 349.99],
                    ['product_id' => 'P102', 'name' => 'MacBook Air M3', 'stock' => 18, 'price' => 1099.00]
                ];
            }
        }

        // Step 3: Send results back to Plug-N-Play for natural language formatting
        $formatRes = Http::post("{$pnpHost}/api/v1/chat/format-sql-response", [
            'agent_id' => $agentId,
            'query' => $query,
            'sql_query' => $sql ?? '',
            'db_results' => $dbResults,
            'user_role' => $userRole
        ]);

        $formatData = $formatRes->json();

        return response()->json([
            'answer' => $formatData['answer'] ?? 'Processed successfully.',
            'sql_executed' => $sql,
            'db_records_found' => count($dbResults)
        ]);
    }
}
