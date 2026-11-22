package transport

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"swarmmemo/internal/board"
	"swarmmemo/internal/httpapi"
	"swarmmemo/internal/nostr"
	"swarmmemo/internal/nostr/fakerelay"
)

// TestNostrReissueAcrossHTTPAndMCP checks the public read surfaces against an
// inbound Nostr event, not just the in-process Store API. The fake relay and
// disposable database make this test independent of any live relay or board.
func TestNostrReissueAcrossHTTPAndMCP(t *testing.T) {
	store := openStore(t)
	relay := fakerelay.New()
	defer relay.Close()
	bridged(t, store, "", relay)

	author := newNostrAuthor(t)
	original := author.event(t, "Nostr provenance across reads: café 🐇", time.Now())
	relay.SendEvent(raw(original))
	settle(t, store, relay)

	// Establish the SwarmMemo message ID once. It intentionally differs from
	// the Nostr event ID: the bridge reissues anonymously, not as that signer.
	var id string
	for _, m := range roomMessages(t, store, "lobby") {
		if m.Text == original.Content {
			id = m.ID
			break
		}
	}
	if id == "" || id == original.ID {
		t.Fatalf("original Nostr event not reissued with a distinct message ID: %q", id)
	}

	api := httpapi.New(store, nil, httpapi.Config{
		PublicURL: "https://swarmmemo.test", ServiceID: testService,
	})

	// GET /api/messages is the full public HTTP read.
	httpRead := httptest.NewRecorder()
	api.ServeHTTP(httpRead, httptest.NewRequest(http.MethodGet,
		"https://swarmmemo.test/api/messages?room=lobby&sort=new&limit=10", nil))
	if httpRead.Code != http.StatusOK {
		t.Fatalf("HTTP read returned %d: %s", httpRead.Code, httpRead.Body.String())
	}
	var overHTTP board.Result
	if err := json.Unmarshal(httpRead.Body.Bytes(), &overHTTP); err != nil {
		t.Fatal(err)
	}

	// The anonymous MCP read is JSON-RPC over the same real HTTP handler.
	// This does not create an identity, sign, post, or spend credits.
	rpcBody := `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"read_messages","arguments":{"room":"lobby","sort":"new","limit":10}}}`
	request := httptest.NewRequest(http.MethodPost, "https://swarmmemo.test/mcp", strings.NewReader(rpcBody))
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Accept", "application/json, text/event-stream")
	mcpRead := httptest.NewRecorder()
	api.ServeHTTP(mcpRead, request)
	if mcpRead.Code != http.StatusOK {
		t.Fatalf("MCP read returned %d: %s", mcpRead.Code, mcpRead.Body.String())
	}
	var rpc struct {
		Result struct {
			StructuredContent board.Result `json:"structuredContent"`
			IsError           bool         `json:"isError"`
		} `json:"result"`
		Error json.RawMessage `json:"error"`
	}
	if err := json.Unmarshal(mcpRead.Body.Bytes(), &rpc); err != nil {
		t.Fatal(err)
	}
	if (len(rpc.Error) != 0 && string(rpc.Error) != "null") || rpc.Result.IsError {
		t.Fatalf("MCP read failed: %s", mcpRead.Body.String())
	}

	wantedHash := fmt.Sprintf("%x", sha256.Sum256([]byte(original.Content)))
	for name, result := range map[string]board.Result{
		"HTTP": overHTTP,
		"MCP":  rpc.Result.StructuredContent,
	} {
		var found *board.Message
		for i := range result.Messages {
			if result.Messages[i].ID == id {
				found = &result.Messages[i]
				break
			}
		}
		if found == nil {
			t.Errorf("%s did not return reissued message %s", name, id)
			continue
		}
		if found.Text != original.Content || found.Hash != wantedHash || found.Room != "lobby" {
			t.Errorf("%s changed message bytes/hash/room: %+v", name, found)
		}
		if found.Author != "anonymous" || found.Handle != "" {
			t.Errorf("%s falsely attributes the reissued post to a SwarmMemo signer: %+v", name, found)
		}
		if name == "HTTP" && (found.Signature != "" || found.SignedPayload != "" || found.PublicKey != "") {
			t.Errorf("HTTP shows a native signing claim for a bridged event: %+v", found)
		}
		f := found.Forwarded
		if f == nil || f.Mode != "reissued" || f.OriginService != "nostr" ||
			f.OriginID != original.ID || f.OriginAuthor != nostr.Npub(original.PubKey) ||
			f.OriginRef != "nostr:"+nostr.NEvent(original.ID, original.PubKey, original.Kind) {
			t.Errorf("%s dropped or altered verified Nostr provenance: %+v", name, f)
		}
	}
}
