from pathlib import Path
from gen.convert_source_language import ParsedCode, RustQuestion
from gen.parsers.common import TAB, extract_code_block, extract_code_blocks

from gen.parsers.go import GoParser


FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_parse_go_code():

    go_code = FIXTURES / "rust-to-go.go"

    results = GoParser.parse(go_code.read_text())

    assert len(results) == 30

    print(results)

def test_extract_code_objects():
    code_file = FIXTURES / "rust-go-11:01:22.367931.md"

    clean_code = extract_code_block(code_file.read_text(), "go")

    print(clean_code)


def test_make_imports():
    imports = ["fmt", "io", "os"]

    results = GoParser.make_imports(imports)

    assert results == f'import (\n{TAB}"fmt"\n{TAB}"io"\n{TAB}"os"\n)\n'


def test_extract_code_blocks():
    code = """
To convert the given Rust struct to Go, we'll need to follow Go's conventions for defining types and manage...

```go
package main

import (
    "sync"
)

// Storer interface, assuming it has some methods that need to be implemented.
type Storer interface{}

// Downloader interface, assuming it has some methods that need to be implemented.
type Downloader interface{}
```

Now, let's define the `TaskManager`. I'm using a simple struct with a `sync.WaitGroup`...

```go
// TaskManager is responsible for managing and synchronizing tasks across goroutines.
type TaskManager struct {
    wg sync.WaitGroup
}

// NewTaskManager creates a new instance of TaskManager.
func NewTaskManager() *TaskManager {
    return &TaskManager{}
}

// Add increments the WaitGroup counter.
func (tm *TaskManager) Add(delta int) {
    tm.wg.Add(delta)
}
```

Finally, let's define the Go version of the `Monitor` struct. Since Go doesn't ...

```go
// Monitor coordinates downloads and tasks.
type Monitor struct {
    store        Storer
    downloads    Downloader
    taskManager  *TaskManager // Using a pointer is Go's way of sharing it between goroutines or functions.
}

// NewMonitor creates a new instance of Monitor with dependencies.
func NewMonitor(store Storer, downloads Downloader, tm *TaskManager) *Monitor {
    return &Monitor{
        store:       store,
        downloads:   downloads,
        taskManager: tm,
    }
}
```

This code defines a `Monitor` struct that holds interfaces for storage and downloading capabilities...
    
    """

    blocks = list(extract_code_blocks(code, "go"))

    assert len(blocks) == 3
