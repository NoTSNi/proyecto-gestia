#!/usr/bin/env python3
"""
Script de testeo del pipeline Document Vault con datos de cliente_ejemplo
"""
import os
import json
import requests
import time

DOCling_URL = "http://localhost:8001/ocr"
EMBEDDING_URL = "http://localhost:8002/embed"

CLIENTE_DIR = "cliente_ejemplo"

def test_ocr(filepath):
    """Prueba OCR con Docling"""
    with open(filepath, 'rb') as f:
        files = {'file': (os.path.basename(filepath), f, 'text/plain')}
        data = {'languages': 'es,en'}
        response = requests.post(DOCling_URL, files=files, data=data, timeout=60)
        return response.json()

def test_embedding(text):
    """Prueba embeddings"""
    response = requests.post(EMBEDDING_URL, json={"text": text}, timeout=30)
    return response.json()

def main():
    print("🧪 TESTEO PIPELINE DOCUMENT VAULT")
    print("=" * 50)
    
    # Cargar metadata
    with open(f"{CLIENTE_DIR}/metadata.json") as f:
        metadata = json.load(f)
    
    cliente = metadata["cliente_ejemplo"]
    print(f"\n📋 Cliente: {cliente['empresa']['nombre']} ({cliente['empresa']['nif']})")
    
    total_docs = 0
    successful = 0
    
    for categoria, docs in cliente["documentos"].items():
        print(f"\n📂 Categoría: {categoria}")
        for doc in docs:
            total_docs += 1
            filepath = f"{CLIENTE_DIR}/{doc['archivo']}"
            
            if not os.path.exists(filepath):
                print(f"  ❌ {doc['archivo']} - NO ENCONTRADO")
                continue
            
            print(f"  📄 {doc['archivo']}...", end=" ")
            
            try:
                # OCR
                ocr_result = test_ocr(filepath)
                text = ocr_result.get("text", "")
                confidence = ocr_result.get("confidence", 0)
                
                if not text:
                    print("❌ Sin texto extraído")
                    continue
                
                # Embedding
                embed_result = test_embedding(text[:1000])  # Primer 1000 chars
                embedding = embed_result.get("embedding", [])
                
                print(f"✅ OCR: {len(text)} chars, conf: {confidence:.2f} | Embedding: {len(embedding)} dims")
                successful += 1
                
            except Exception as e:
                print(f"❌ Error: {e}")
            
            time.sleep(0.5)  # Rate limiting
    
    print(f"\n{'='*50}")
    print(f"📊 RESULTADOS: {successful}/{total_docs} documentos procesados OK")
    
    if successful == total_docs:
        print("🎉 TESTEO COMPLETADO CON ÉXITO")
    else:
        print("⚠️  Algunos documentos fallaron")

if __name__ == "__main__":
    main()