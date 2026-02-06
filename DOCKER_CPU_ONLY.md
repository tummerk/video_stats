# CPU-Only Docker Build Verification

## Как это работает

### Порядок установки в Dockerfile.worker

1. **Сначала устанавливается CPU-only PyTorch:**
   ```dockerfile
   RUN pip install --no-cache-dir \
       torch==2.1.0+cpu \
       torchvision==0.16.0+cpu \
       torchaudio==2.1.0+cpu \
       --index-url https://download.pytorch.org/whl/cpu
   ```

2. **Затем устанавливается openai-whisper:**
   ```dockerfile
   RUN pip install --no-cache-dir -r requirements.worker.txt
   ```
   Pip видит, что torch уже установлен и не переустанавливает его.

3. **Проверка после установки:**
   ```dockerfile
   RUN python -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA available:', torch.cuda.is_available())"
   ```
   Должен показать: `CUDA available: False`

## Проверка отсутствия NVIDIA пакетов

### При сборке образа
```bash
docker compose build worker
```
Ищите: `Successfully installed torch-2.1.0+cpu`
НЕ должно быть: `nvidia-cuda-*` или `torch-2.1.0+cu*`

### Внутри контейнера
```bash
docker compose run --rm worker python -c "import torch; print('CUDA:', torch.cuda.is_available())"
# Ожидаемый вывод: CUDA: False
```

### Размер образа
- CPU-only: ~1.1-1.5 GB
- С NVIDIA: ~3-5 GB
- Экономия: ~2-3.5 GB
