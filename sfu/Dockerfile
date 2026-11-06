FROM golang:1.24-alpine AS builder

# Install build dependencies for CGO (Opus, gRPC) and git for module resolution
RUN apk add --no-cache \
    protobuf-dev \
    protoc \
    gcc \
    musl-dev \
    pkgconf \
    opus-dev \
    opusfile-dev \
    git

# Install Go plugins for protoc
RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
RUN go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.5.1
ENV PATH="$PATH:$(go env GOPATH)/bin"

WORKDIR /app

# Copy go.mod first
COPY go.mod ./
RUN go mod download

# Copy the entire project
COPY . .

# Stubs must exist before `go mod tidy`, or it tries to fetch the proto package from GitHub
# Generate gRPC stubs into the correct directory
RUN protoc --go_out=. --go_opt=paths=source_relative \
    --go-grpc_out=. --go-grpc_opt=paths=source_relative \
    grpc/proto/sfu.proto

# Explicitly fetch compatible dependencies and sync
RUN go get github.com/hraban/opus@latest
RUN go mod tidy && go mod download


# Build the application
RUN go vet ./... && go test ./... && go build -o pion-sfu .

FROM alpine:latest
# Install runtime libraries
RUN apk add --no-cache opus opusfile

WORKDIR /app
COPY --from=builder /app/pion-sfu .
EXPOSE 50051 8080
CMD ["./pion-sfu"]
