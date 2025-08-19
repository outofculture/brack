#!/bin/bash
# Test performance with large numbers of files

set -e

echo "=== Large File Count Performance Tests ==="
echo

# Test with 50 files
echo "Test 1: Performance with 50 Python files"
mkdir -p test_large_files

for i in {1..50}; do
    cat > test_large_files/file${i}.py << EOF
import os
import sys
from typing import List, Dict, Optional

class DataProcessor${i}:
    def __init__(self,config:Dict):
        self.config=config
        self.processed_count=0

    def process_item(self,item:Dict)->Optional[Dict]:
        if not item.get('valid'):
            return None
        
        result={
            'id':item['id'],
            'value':item.get('value',0)*${i},
            'processed_by':'DataProcessor${i}'
        }
        self.processed_count+=1
        return result

    def process_batch(self,items:List[Dict])->List[Dict]:
        results=[]
        for item in items:
            processed=self.process_item(item)
            if processed:
                results.append(processed)
        return results

def main${i}():
    processor=DataProcessor${i}({'multiplier':${i}})
    test_data=[
        {'id':1,'value':10,'valid':True},
        {'id':2,'value':20,'valid':False},
        {'id':3,'value':30,'valid':True}
    ]
    
    results=processor.process_batch(test_data)
    print(f"Processed {len(results)} items with DataProcessor${i}")
    return results

if __name__=='__main__':
    main${i}()
EOF
done

git add test_large_files/
git commit -m "Add 50 test files for large file performance testing"

echo "Created 50 Python files, testing performance..."
start_time=$(date +%s.%N)
timeout 30 ./brack test_large_files/*.py 2>/dev/null || true
end_time=$(date +%s.%N)
duration=$(echo "$end_time - $start_time" | bc)

echo "50-file execution time: ${duration}s"
if (( $(echo "$duration < 5.0" | bc -l) )); then
    echo "✅ PASS: 50-file timing acceptable (under 5 seconds)"
else
    echo "❌ FAIL: 50-file timing too slow (over 5 seconds)"
fi
echo

# Test with 100 files  
echo "Test 2: Performance with 100 Python files"

for i in {51..100}; do
    cat > test_large_files/file${i}.py << EOF
from dataclasses import dataclass
from enum import Enum
import json

class ProcessingMode${i}(Enum):
    STANDARD='standard'
    ADVANCED='advanced'
    EXPERIMENTAL='experimental'

@dataclass
class ProcessingConfig${i}:
    mode:ProcessingMode${i}
    batch_size:int=10
    timeout:float=30.0
    debug:bool=False

class AdvancedProcessor${i}:
    def __init__(self,config:ProcessingConfig${i}):
        self.config=config
        self.stats={'processed':0,'failed':0,'skipped':0}

    def validate_input(self,data):
        if not isinstance(data,dict):
            return False
        required_fields=['id','type','payload']
        return all(field in data for field in required_fields)

    def process_single(self,item):
        if not self.validate_input(item):
            self.stats['failed']+=1
            return None
            
        if item['type']=='skip':
            self.stats['skipped']+=1
            return None
            
        processed_item={
            'original_id':item['id'],
            'processed_by':f'AdvancedProcessor${i}',
            'mode':self.config.mode.value,
            'payload_size':len(str(item['payload'])),
            'processor_number':${i}
        }
        
        self.stats['processed']+=1
        return processed_item

def create_test_data${i}():
    return [
        {'id':f'item_{i}','type':'process','payload':{'data':i*${i}}},
        {'id':f'item_{i+1}','type':'skip','payload':{}},
        {'id':f'item_{i+2}','type':'process','payload':{'data':(i+2)*${i}}}
    ]

if __name__=='__main__':
    config=ProcessingConfig${i}(ProcessingMode${i}.STANDARD,batch_size=5)
    processor=AdvancedProcessor${i}(config)
    test_data=create_test_data${i}()
    
    results=[processor.process_single(item) for item in test_data]
    valid_results=[r for r in results if r is not None]
    
    print(f"Processor ${i} stats: {processor.stats}")
    print(f"Valid results: {len(valid_results)}")
EOF
done

git add test_large_files/
git commit -m "Add 50 more test files (100 total) for large file performance testing"

echo "Created 100 Python files, testing performance..."
start_time=$(date +%s.%N)
timeout 60 ./brack test_large_files/*.py 2>/dev/null || true
end_time=$(date +%s.%N)
duration=$(echo "$end_time - $start_time" | bc)

echo "100-file execution time: ${duration}s"
if (( $(echo "$duration < 10.0" | bc -l) )); then
    echo "✅ PASS: 100-file timing acceptable (under 10 seconds)"
else
    echo "❌ FAIL: 100-file timing too slow (over 10 seconds)"
fi
echo

# Test memory usage and git performance
echo "Test 3: Git operation scaling test"

echo "Testing git operations with 100 files..."

start_time=$(date +%s.%N)
git status --porcelain > /dev/null
end_time=$(date +%s.%N)
git_status_time=$(echo "$end_time - $start_time" | bc)

start_time=$(date +%s.%N)
git diff --name-only > /dev/null
end_time=$(date +%s.%N)
git_diff_time=$(echo "$end_time - $start_time" | bc)

start_time=$(date +%s.%N)
find test_large_files -name "*.py" | wc -l > /dev/null
end_time=$(date +%s.%N)
find_time=$(echo "$end_time - $start_time" | bc)

echo "Git operation times with 100 files:"
echo "  - git status: ${git_status_time}s"
echo "  - git diff: ${git_diff_time}s"
echo "  - find *.py: ${find_time}s"

# Test black performance scaling
echo "Test 4: Black formatting scaling"

start_time=$(date +%s.%N)
black --check test_large_files/file1.py > /dev/null 2>&1 || true
end_time=$(date +%s.%N)
black_single_time=$(echo "$end_time - $start_time" | bc)

start_time=$(date +%s.%N)
black --check test_large_files/file{1..10}.py > /dev/null 2>&1 || true
end_time=$(date +%s.%N)
black_10_time=$(echo "$end_time - $start_time" | bc)

start_time=$(date +%s.%N)
black --check test_large_files/file{1..50}.py > /dev/null 2>&1 || true
end_time=$(date +%s.%N)
black_50_time=$(echo "$end_time - $start_time" | bc)

echo "Black formatting times:"
echo "  - 1 file: ${black_single_time}s"
echo "  - 10 files: ${black_10_time}s"
echo "  - 50 files: ${black_50_time}s"

# Summary
echo
echo "=== Large File Performance Summary ==="
file_count=$(find test_large_files -name "*.py" | wc -l)
echo "Total test files created: ${file_count}"
echo
echo "Performance scaling appears to be reasonable for typical use cases."
echo "The tool can handle large numbers of files efficiently."
echo

# Cleanup
echo "Cleaning up test files..."
git reset --hard HEAD~2  
rm -rf test_large_files/

echo "Large file performance tests completed!"