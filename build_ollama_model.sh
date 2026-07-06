#!/usr/bin/env bash
set -e

########################################
# CONFIGURATION
########################################
MODEL_DIR="same_prompt_model_merged"
OLLAMA_MODEL_NAME="same_prompt_ollama_model"

# Choose ONE: q4_k_m | q5_k_m | q8_0 | Q4_K_S
QUANTIZATION="Q4_K_S"

########################################
# STEP 1: Go to merged model directory
########################################
echo "📂 Entering model directory: $MODEL_DIR"

if [ ! -d "$MODEL_DIR" ]; then
  echo "❌ Error: Directory '$MODEL_DIR' not found"
  exit 1
fi

cd "$MODEL_DIR"

########################################
# STEP 2: Create Modelfile
########################################
echo "📝 Creating Modelfile in $(pwd)"

cat > Modelfile << 'EOF'
FROM .

PARAMETER num_ctx 4096
PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER top_k 20

TEMPLATE """{{ if .System }}<|start_header_id|>system<|end_header_id|>

{{ .System }}<|eot_id|>{{ end }}{{ range $i, $_ := .Messages }}{{ if eq .Role "user" }}<|start_header_id|>user<|end_header_id|>

{{ if .Content }}{{ .Content }}{{ end }}{{ if .Images }}<|image|>{{ range .Images }}<|image|>{{ end }}{{ end }}<|eot_id|>{{ else if eq .Role "assistant" }}<|start_header_id|>assistant<|end_header_id|>

{{ .Content }}<|eot_id|>{{ end }}{{ end }}<|start_header_id|>assistant<|end_header_id|>

"""

SYSTEM "You are a helpful vision-and-language assistant using your fine-tuned knowledge."
EOF

########################################
# STEP 3: Build Ollama model
########################################
echo "🧠 Building Ollama model: $OLLAMA_MODEL_NAME"
echo "⚙️  Quantization: $QUANTIZATION"

ollama create "$OLLAMA_MODEL_NAME" -f Modelfile --quantize "$QUANTIZATION"

########################################
# STEP 4: Verify
########################################
echo "✅ Model build completed"
echo "📦 Ollama models:"
ollama list

