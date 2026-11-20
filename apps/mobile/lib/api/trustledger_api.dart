import 'api_client.dart';

/// Typed wrappers around the TrustLedger REST API.
class TrustLedgerApi {
  TrustLedgerApi(this.client);

  final ApiClient client;

  Future<List<dynamic>> personas() async => await client.get('/demo/personas') as List<dynamic>;

  Future<void> resetDemo() async => client.post('/demo/reset');

  Future<void> startSession(String userId) async {
    final resp = await client.post('/auth/session', {'user_id': userId}) as Map<String, dynamic>;
    client.token = resp['token'] as String;
  }

  Future<void> grantConsent(String userId, String source) =>
      client.post('/consent', {'user_id': userId, 'source': source});

  Future<void> revokeConsent(String source) => client.delete('/consent/$source');

  Future<Map<String, dynamic>> me() async => await client.get('/me') as Map<String, dynamic>;

  Future<Map<String, dynamic>> apply(String userId, double amount, {List<String>? sms}) async =>
      await client.post('/apply', {'user_id': userId, 'amount_bdt': amount, 'sms': ?sms}) as Map<String, dynamic>;

  Future<Map<String, dynamic>> uploadDocument(String userId, List<int> bytes, String filename) async =>
      await client.postFile('/documents', {'user_id': userId, 'document_type': 'utility_bill'}, bytes, filename)
          as Map<String, dynamic>;

  Future<Map<String, dynamic>> bhorshaStart(String userId) async =>
      await client.post('/bhorsha/start', {'user_id': userId}) as Map<String, dynamic>;

  Future<Map<String, dynamic>> bhorshaAnswer(String sessionId, String answer, double elapsed) async =>
      await client.post('/bhorsha/$sessionId/answer', {'answer': answer, 'elapsed_seconds': elapsed})
          as Map<String, dynamic>;

  Future<Map<String, dynamic>> bhorshaResult(String sessionId) async =>
      await client.get('/bhorsha/$sessionId/result') as Map<String, dynamic>;

  Future<Map<String, dynamic>> loan(String applicationId) async =>
      await client.get('/loans/$applicationId') as Map<String, dynamic>;

  Future<Map<String, dynamic>> disburse(String applicationId) async =>
      await client.post('/loans/$applicationId/disburse') as Map<String, dynamic>;

  Future<Map<String, dynamic>> repay(String applicationId, double amount, String key) async =>
      await client.post('/loans/$applicationId/repayments', {
            'amount_bdt': amount,
            'on_time': true,
            'idempotency_key': key,
          })
          as Map<String, dynamic>;

  Future<Map<String, dynamic>> upgradeLimit(String applicationId) async =>
      await client.post('/loans/$applicationId/limit-upgrade') as Map<String, dynamic>;

  Future<void> deleteMe() => client.delete('/me');
}
