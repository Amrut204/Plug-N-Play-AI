<?php
// routes/api.php — Laravel API Route for Plug-N-Play AI Zero-Knowledge Bridge

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\AIChatController;

Route::post('/ai-chat', [AIChatController::class, 'handleChat']);
