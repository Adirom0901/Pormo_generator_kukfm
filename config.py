# to store all main setttings in one place

#local model huggingface link
MODEL_REPO = "bartowski/Qwen2.5-7B-Instruct-GGUF"
MODEL_FILE = "Qwen2.5-7B-Instruct-Q4_K_M.gguf"
N_CTX = 8192

#settings for promos to be built
MIN_PROMO_SECONDS = 20
MAX_PROMO_SECONDS = 60
MAX_HOOK_SECONDS = 20

#max retries to be expected from model
MAX_TRIES = 2