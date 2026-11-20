import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trustledger_app/api/api_client.dart';

void main() {
  test('retries server errors then succeeds', () async {
    var calls = 0;
    final client = ApiClient(
      baseUrl: 'http://x',
      baseDelay: Duration.zero,
      client: MockClient((_) async {
        calls++;
        return calls < 3 ? http.Response('boom', 503) : http.Response('{"ok": true}', 200);
      }),
    );
    expect(await client.get('/health'), {'ok': true});
    expect(calls, 3);
  });

  test('network failure becomes a Bangla-mapped network error', () async {
    final client = ApiClient(
      baseUrl: 'http://x',
      baseDelay: Duration.zero,
      client: MockClient((_) async => throw http.ClientException('offline')),
    );
    await expectLater(
      client.get('/health'),
      throwsA(isA<ApiException>().having((e) => e.l10nKey, 'key', 'err_network')),
    );
  });

  test('consent errors are not retried', () async {
    var calls = 0;
    final client = ApiClient(
      baseUrl: 'http://x',
      client: MockClient((_) async {
        calls++;
        return http.Response('{"error": "CONSENT_MISSING", "detail": "x"}', 403);
      }),
    );
    await expectLater(client.post('/score'), throwsA(isA<ApiException>().having((e) => e.kind, 'kind', 'consent')));
    expect(calls, 1);
  });
}
