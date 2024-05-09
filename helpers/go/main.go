package main

import (
	"encoding/json"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"log"
	"os"
	"strings"
)

type Item struct {
    Name     string `json:"name"`
    ItemType string `json:"type"`
    Source   string `json:"source"`
    Receiver string `json:"receiver,omitempty"`
}

func main() {
    if len(os.Args) < 2 {
        fmt.Println("Usage: go run main.go <filename>")
        os.Exit(1)
    }

    filename := os.Args[1]
    source, err := os.ReadFile(filename)
    if err != nil {
        log.Fatal(err)
    }

    fset := token.NewFileSet()
    node, err := parser.ParseFile(fset, filename, nil, parser.ParseComments)
    if err != nil {
        fmt.Println("Error parsing file:", err)
        os.Exit(1)
    }

    var items []Item
    seenNames := map[string]bool{}
    var imports []string

    for _, decl := range node.Decls {
        var item Item
        switch d := decl.(type) {
        case *ast.GenDecl:
            for _, spec := range d.Specs {
                switch s := spec.(type) {
                case *ast.TypeSpec:
                    item.Name = s.Name.Name
                    item.ItemType = "Type"
                    item.Source = getTypeSource(source, spec, fset)
                case *ast.ValueSpec:
                    for _, name := range s.Names {
                        if seenNames[name.Name] {
                            continue
                        }
                        seenNames[name.Name] = true
                        item.Name = name.Name
                        item.ItemType = "Value"
                        item.Source = getValueSource(source, spec, fset)
                        items = append(items, item)
                    }
                    continue
                case *ast.ImportSpec:
                    imports = append(imports, strings.ReplaceAll(s.Path.Value, "\"", ""))
                    continue
                default:
                    println("Unknown spec type")
                }

                if seenNames[item.Name] {
                    continue
                }
                seenNames[item.Name] = true
                items = append(items, item)
            }
        case *ast.FuncDecl:
            item.Name = d.Name.Name
            item.ItemType = "Function"
            item.Source, item.Receiver = getFunctionSource(source, decl, fset)
        default:
            println("Unknown decl type")
        }

        if seenNames[item.Name] {
            continue
        }
        seenNames[item.Name] = true

        if item.Name != "" {
            items = append(items, item)
        }
    }

    items = append(items, Item{Name: "import", ItemType: "import", Source: strings.Join(imports, ",")})

    jsonOutput, err := json.MarshalIndent(items, "", "  ")
    if err != nil {
        fmt.Println("Error marshalling to JSON:", err)
        os.Exit(1)
    }

    fmt.Println(string(jsonOutput))
}


func getFunctionSource(source []uint8, decl ast.Decl, fset *token.FileSet) (string, string) {
    if fn, isFn := decl.(*ast.FuncDecl); isFn {
        // Check if the function has a receiver
        var receiver string
        if fn.Recv != nil && len(fn.Recv.List) > 0 {
            // Extract the receiver type
            recvType := fn.Recv.List[0].Type
            if starExpr, isStar := recvType.(*ast.StarExpr); isStar {
                // The receiver is a pointer type
                recvType = starExpr.X
            }
            receiver = exprToString(recvType)
        }

        startPos := fset.Position(fn.Pos()).Offset
        // Include comments if they exist
        if fn.Doc != nil {
            docPos := fset.Position(fn.Doc.Pos())
            startPos = docPos.Offset
        }

        endPos := fset.Position(fn.End())

        // Extract the source code for the function
        return string(source[startPos:endPos.Offset]), receiver
    }
    return "", ""
}

/*
func getSource(source []byte, spec ast.Spec, fset *token.FileSet) string {
    var startPos, endPos token.Pos

    switch v := spec.(type) {
    case *ast.ValueSpec:
        startPos, endPos = v.Pos(), v.End()
        if v.Doc != nil {
            startPos = v.Doc.Pos()
        }
    case *ast.TypeSpec:
        startPos, endPos = v.Pos(), v.End()
        if v.Doc != nil {
            startPos = v.Doc.Pos()
        }
    default:
        return ""
    }

    startOffset := fset.Position(startPos).Offset
    endOffset := fset.Position(endPos).Offset

    return string(source[startOffset:endOffset])
}*/

func getValueSource(source []uint8, spec ast.Spec, fset *token.FileSet) string {
    if valueSpec, isValueSpec := spec.(*ast.ValueSpec); isValueSpec {
        startPos := fset.Position(valueSpec.Pos()).Offset
        var prefix string

        // Include comments if they exist
        if valueSpec.Doc != nil {
            startPos = fset.Position(valueSpec.Doc.Pos()).Offset
        } else {
            switch valueSpec.Names[0].Obj.Kind.String() {
            case "var":
                prefix = "var "
            case "const":
                prefix = "const "
            default:
                println("Unknown kind")
            }
        }

        endPos := fset.Position(valueSpec.End())

        // Extract the source code for the type definition
        return prefix + string(source[startPos:endPos.Offset])
    }
    
    return ""
}

func getTypeSource(source []uint8, spec ast.Spec, fset *token.FileSet) string {
    if typeSpec, isTypeSpec := spec.(*ast.TypeSpec); isTypeSpec {
        startPos := fset.Position(typeSpec.Pos()).Offset
        var prefix string

        // Include comments if they exist
        if typeSpec.Doc != nil {
            startPos = fset.Position(typeSpec.Doc.Pos()).Offset
        } else {
            switch typeSpec.Name.Obj.Kind.String() {
            case "type":
                prefix = "type "
            default:
                println("Unknown kind")
            }
        }

        endPos := fset.Position(typeSpec.End())

        // Extract the source code for the type definition
        return prefix + string(source[startPos:endPos.Offset])
    }
    
    return ""
}

func exprToString(expr ast.Expr) string {
    switch e := expr.(type) {
    case *ast.Ident:
        return e.Name
    case *ast.SelectorExpr:
        return exprToString(e.X) + "." + e.Sel.Name
    default:
        return ""
    }
}
