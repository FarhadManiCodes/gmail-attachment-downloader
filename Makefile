.PHONY: build test clean dev

build:
	@go build -o bin/gmail-downloader ./cmd/gmail-downloader

test:
	@go test ./...

clean:
	@rm -rf bin/

dev: test build
	@echo "✅ Development cycle complete"
	@echo "   Try: ./bin/gmail-downloader --help"
