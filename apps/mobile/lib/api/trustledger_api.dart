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

  /// [documentType] null lets the server detect the type (bill, receipt or khata page).
  Future<Map<String, dynamic>> uploadDocument(
    String userId,
    List<int> bytes,
    String filename, {
    String? documentType = 'utility_bill',
  }) async =>
      await client.postFile('/documents', {'user_id': userId, 'document_type': ?documentType}, bytes, filename)
          as Map<String, dynamic>;

  Future<Map<String, dynamic>> bhorshaStart(String userId) async =>
      await client.post('/bhorsha/start', {'user_id': userId}) as Map<String, dynamic>;

  Future<Map<String, dynamic>> bhorshaAnswer(String sessionId, String answer, double elapsed) async =>
      await client.post('/bhorsha/$sessionId/answer', {'answer': answer, 'elapsed_seconds': elapsed})
          as Map<String, dynamic>;

  Future<Map<String, dynamic>> bhorshaResult(String sessionId) async =>
      await client.get('/bhorsha/$sessionId/result') as Map<String, dynamic>;

  Future<Map<String, dynamic>> explain(String decisionId) async =>
      await client.get('/explain/$decisionId') as Map<String, dynamic>;

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

  Future<Map<String, dynamic>> registerUser({
    String? phone,
    String gender = 'F',
    String region = 'urban',
    String division = 'Dhaka',
  }) async {
    final resp = await client.post('/auth/register', {
      'phone': ?phone,
      'gender': gender,
      'region': region,
      'division': division,
    }) as Map<String, dynamic>;
    client.token = resp['token'] as String;
    return resp;
  }

  Future<Map<String, dynamic>> uploadSms(
    String userId, {
    List<int>? bytes,
    String? filename,
    String? rawText,
  }) async {
    if (bytes != null && filename != null) {
      return await client.postFile('/upload/sms', {'user_id': userId}, bytes, filename)
          as Map<String, dynamic>;
    }
    return await client.post('/upload/sms', {'user_id': userId, 'raw_text': ?rawText})
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> confirmUpload(
    String userId,
    List<dynamic> transactions, {
    List<dynamic>? billRecords,
    double requestedAmount = 15000,
  }) async {
    return await client.post('/upload/confirm', {
      'user_id': userId,
      'transactions': transactions,
      'bill_records': billRecords ?? [],
      'requested_amount_bdt': requestedAmount,
    }) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> aiHealth() async =>
      await client.get('/health/ai') as Map<String, dynamic>;

  Future<void> deleteMe() => client.delete('/me');
}
