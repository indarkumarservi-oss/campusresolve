import pandas as pd
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ai.ai_utils import train_models

if __name__ == '__main__':
    print("Training AI models...")
    metadata = train_models()
    print(f"Training complete!")
    print(f"Dataset records: {metadata['dataset_records']}")
    print(f"Category accuracy: {metadata['category_accuracy']:.4f}")
    print(f"Priority accuracy: {metadata['priority_accuracy']:.4f}")
    print(f"Categories: {metadata['categories']}")
    print(f"Priorities: {metadata['priorities']}")
    print(f"Model files saved to models/")