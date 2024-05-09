

.PHONY: go_parser
go_parser:
	go build -o bin/go_parser helpers/go/main.go

.PHONY: rust_parser
rust_parser:
	cargo build -r
	mv target/release/rust_parser bin/rust_parser
