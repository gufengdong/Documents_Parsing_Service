uv pip install httpx[socks]
uv pip install -U "mineru[core]"
uv pip install -U openai


curl -sS -X POST 'http://10.36.244.180:30012/v1/chat/completions' \ -H "Authorization: Bearer sk-8b9e93931f6e4051b750588b4bbb2856" \ -H 'Content-Type: application/json' \ -d "{ \"model\": \"MiniCPM-V-4_5\", \"messages\": [ { \"role\": \"user\", \"content\": [ {\"type\":\"text\",\"text\":\"请用中文描述这张图片的主要内容。\"}, {\"type\":\"image_url\",\"image_url\":{\"url\":\"data:image/png;base64,${IMG_B64}\"}} ] } ], \"max_tokens\": 512, \"temperature\": 0.2, \"stream\": false }"



cat > payload.json <<EOF
{
  "model": "MiniCPM-V-4_5",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "请用中文描述这张图片的主要内容。"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64;base64:${IMG_B64}"}}
      ]
    }
  ],
  "max_tokens": 512,
  "temperature": 0.2,
  "stream": false
}
EOF



curl -s -X 'POST'   'http://10.57.9.13:8086/v1/convert/file'   -H 'accept: application/json'   -H 'Content-Type: multipart/form-data'     -F 'files=@123.pdf;type=application/pdf'      -F 'to_formats=md'   -F 'image_export_mode=embedded'     -F 'do_ocr=true'   -F 'force_ocr=false'   -F 'ocr_engine=easyocr'     -F 'table_mode=accurate'   -F 'do_table_structure=true'   -F 'include_images=true'     -F 'do_picture_description=true'   -F 'picture_description_area_threshold=0.0'     -F 'picture_description_api={
    "url": "http://10.36.244.180:30012/v1/chat/completions",
    "headers": {
      "Authorization": "Bearer sk-8b9e93931f6e4051b750588b4bbb2856"
    },
    "params": {
      "model": "MiniCPM-V-4_5",
      "max_completion_tokens": 512,
      "temperature": 0.2,
      "stream": false
    },
    "timeout": 60,
    "concurrency": 2,
    "prompt": "请用中文描述这张图片的主要内容。",
    "response_format": "text"
  }'     | jq -r '.document.md_content' > output.md


curl -s -X 'POST' \
  'http://10.57.9.13:8086/v1/convert/source' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "sources": [
      {
        "kind": "http",
        "url": "https://arxiv.org/pdf/2501.17887"
      }
    ],
    "options": {
      "to_formats": ["md"],
      "image_export_mode": "embedded",

      "do_ocr": true,
      "force_ocr": false,
      "ocr_engine": "easyocr",

      "table_mode": "accurate",
      "do_table_structure": true,
      "include_images": true,

      "do_picture_description": false,
      "picture_description_area_threshold": 0.0,

      "picture_description_api": {
        "url": "http://10.36.244.180:30012/v1/chat/completions",
        "headers": {
          "Authorization": "Bearer sk-8b9e93931f6e4051b750588b4bbb2856"
        },
        "params": {
          "model": "MiniCPM-V-4_5",
          "max_completion_tokens": 512,
          "temperature": 0.2,
          "stream": false
        },
        "timeout": 60,
        "concurrency": 2,
        "prompt": "请用中文描述这张图片的主要内容。",
        "response_format": "text"
      }
    }
  }' \
  | jq -r '.document.md_content' > output1.md



curl -s -X 'POST'   'http://10.57.9.13:8086/v1/convert/file'   -H 'accept: application/json'   -H 'Content-Type: multipart/form-data'     -F 'files=@456.pdf;type=application/pdf'      -F 'to_formats=md'   -F 'image_export_mode=embedded'     -F 'do_ocr=false'   -F 'force_ocr=false'   -F 'ocr_engine=easyocr'     -F 'table_mode=accurate'   -F 'do_table_structure=true'   -F 'include_images=true'     -F 'do_picture_description=true'   -F 'picture_description_area_threshold=0.0'     -F 'picture_description_api={
    "url": "http://10.36.244.180:30012/v1/chat/completions",
    "headers": {
      "Authorization": "Bearer sk-8b9e93931f6e4051b750588b4bbb2856"
    },
    "params": {
      "model": "MiniCPM-V-4_5",
      "max_completion_tokens": 1024,
      "temperature": 0.2,
      "stream": false
    },
    "timeout": 60,
    "concurrency": 6,
    "prompt": "请用中文描述这张图片的主要内容。",
    "response_format": "text"
  }'     | jq -r '.document.md_content' > output2.md

curl -s -X 'POST'   'http://10.57.9.13:8086/v1/convert/file'   -H 'accept: application/json'   -H 'Content-Type: multipart/form-data'     -F 'files=@专项月报_AI经验知识库_月报汇报材料0905.pptx;type=application/pdf'      -F 'to_formats=md'   -F 'image_export_mode=embedded'     -F 'do_ocr=true'   -F 'force_ocr=false'   -F 'ocr_engine=easyocr'     -F 'table_mode=accurate'   -F 'do_table_structure=true'   -F 'include_images=true'     -F 'do_picture_description=false'   -F 'picture_description_area_threshold=0.0'     | jq -r '.document.md_content' > output4.md

<!-- uvicorn projects.docling_compat.app:app --host 0.0.0.0 --port 8086 --env-file .env -->




eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1MzM2NjI0Zi02NTNiLTQwZWEtODBiYy05MDViZGY5ZTViODMiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY2NzMzMDQ5fQ.0ASyzdcfrSBBlm0FExvN3ov1NVuLzH7wz3v1LzvpKwM

curl -i \
  -H "X-N8N-API-KEY: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1MzM2NjI0Zi02NTNiLTQwZWEtODBiYy05MDViZGY5ZTViODMiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY2NzMzMTUwfQ.iAmvgx2ZJvmWUlC2lt2Xk-MASX-I4Ljbj6Ug846twbk" \
http://10.57.9.13:5678/api/v1/workflows



python3 - <<'PY'
from jose import jwt
import time

payload = {
    "sub": "user-1",
    "request_id": "req-1",
    "iss": "langflow",
    "iat": int(time.time()),
    "exp": int(time.time()) + 300,
}

token = jwt.encode(payload, "change-me", algorithm="HS256")
print(token)
PY


  curl -X POST http://localhost:8001/api/v1/triggers/sync \
    -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEiLCJyZXF1ZXN0X2lkIjoicmVxLTEiLCJpc3MiOiJsYW5nZmxvdyIsImlhdCI6MTc2Njc1MzE4MiwiZXhwIjoxNzY2NzUzNDgyfQ.fO8nJCmTDLKLNSGhesz7a2ZuYxqL0mJMYaeGaNzmYn0" \
    -H "Idempotency-Key: idem-3" \
    -H "Content-Type: application/json" \
    -d '{
      "trigger_config_id":"tc-1",
      "flow_id":"flow-1",
      "enabled":true,
      "schedule":{"type":"daily","time":"09:30","timezone":"Asia/Shanghai"}
    }'

  curl -X POST http://localhost:8001/api/v1/triggers/sync \
    -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEiLCJyZXF1ZXN0X2lkIjoicmVxLTEiLCJpc3MiOiJsYW5nZmxvdyIsImlhdCI6MTc2Njc1MzE4MiwiZXhwIjoxNzY2NzUzNDgyfQ.fO8nJCmTDLKLNSGhesz7a2ZuYxqL0mJMYaeGaNzmYn0" \
    -H "Idempotency-Key: idem-5" \
    -H "Content-Type: application/json" \
    -d '{
      "trigger_config_id":"tc-1",
      "flow_id":"flow-1",
      "owner_user_id":"user-1",
      "version":5,
      "enabled":true,
      "schedule":{"type":"daily","time":"09:30","timezone":"Asia/Shanghai"}
    }'


 docker compose -f docker-compose.gateway.yml exec gateway \
    curl -i -H "X-N8N-API-KEY: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1MzM2NjI0Zi02NTNiLTQwZWEtODBiYy05MDViZGY5ZTViODMiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY2NzMzMDQ5fQ.0ASyzdcfrSBBlm0FExvN3ov1NVuLzH7wz3v1LzvpKwM" http://10.57.9.13:5678/api/v1/workflows



# VRAM_PER_TASK
# DOC_COMPAT_LOG_RSS=1
# DOC_COMPAT_MARKER_LOWRES_DPI=72
# DOC_COMPAT_MARKER_HIGHRES_DPI=144
# CONVERT_POOL_RECYCLE_TASKS=30
# # === MinIO 配置 ===
# # MINIO_ENDPOINT=http://192.168.88.118:9000        
# # # 访问地址，包含协议和端口
# # MINIO_ACCESS_KEY=minioadmin                 
# # # 访问凭证
# # MINIO_SECRET_KEY=minioadmin                 
# # 访问凭证
# MINIO_REGION=                   
# # 如未使用可留空
# MINIO_USE_SSL=false                         
# # 使用 https 时改为 true
# MINIO_BUCKET_DOCS=docling-markdown  
# MINIO_BUCKET_MARKDOWN_IMAGES=markdown-image
# # 存放 Markdown
# MINIO_BUCKET_TOKENIZER=tokenizer-pretty     
# # 存放 pretty JSON / 其它产物
# MINIO_BUCKET_RAW_V2=raw-uploads-v2

# MINIO_ENDPOINT=http://10.36.244.180:30030
# MINIO_ACCESS_KEY=admin
# MINIO_SECRET_KEY=admin1234
# sudo fuser -k 8086/tcp

# MARKER_DTYPE=float16
# source .venv/bin/activate
# uvicorn projects.docling_compat.app:app   --host 0.0.0.0   --port 8086   --env-file .env   
# export AZURE_OPENAI_API_KEY="2orzP6DXut7ZhslKweuhdnpIQypXgpgG1nlbsfCR9ayLP15rdFmyJQQJ99BJACHYHv6XJ3w3AAAAACOGocgA"
# export https_proxy=http://127.0.0.1:7890 http_proxy=http://127.0.0.1:7890 all_proxy=socks5://127.0.0.1:7890

# uvicorn projects.docling_compat.app:app   --host 0.0.0.0   --port 8086   --env-file .env  --workers 1
# nvidia-smi -i 1 \
#   --query-gpu=timestamp,memory.used,memory.total,utilization.gpu \
#   --format=csv -l 2
#  sudo dmesg -T | egrep -i 'killed process|oom|out of memory'
# watch -n 2 "free -h; ps --ppid 1090714 -o pid,rss,etime,cmd --sort=-rss"
<!-- python scripts/cythonize_core.py build_ext --inplace
bash scripts/strip_cython_sources.sh-->

<!-- • - 找到服务 PID：pgrep -af "uvicorn projects.docling_compat.app:app.*--port 8086"
  - 看该 PID 下面的转换 worker（RSS 单位 KB）：ps --ppid <UVICORN_PID> -o pid,ppid,rss,etime,cmd --sort=-rss
  - 只看转换子进程（spawn_main）：ps --ppid <UVICORN_PID> -o pid,rss,etime,cmd --sort=-rss | rg "multiprocessing\\.spawn|spawn_main"
  - 实时观察：watch -n 2 "ps --ppid <UVICORN_PID> -o pid,rss,etime,cmd --sort=-rss; echo; free -h"
  - 看显存（可选）：nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader | sort -t, -k3 -nr -->