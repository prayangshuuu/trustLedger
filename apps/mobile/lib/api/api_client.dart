import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

/// API error with a category the UI maps to a Bangla message.
class ApiException implements Exception {
  ApiException(this.kind, this.message, {this.status});

  /// network | server | consent | client
  final String kind;
  final String message;
  final int? status;

  String get l10nKey => switch (kind) {
    'network' => 'err_network',
    'server' => 'err_server',
    'consent' => 'err_consent',
    _ => 'err_generic',
  };

  @override
  String toString() => 'ApiException($kind, $status, $message)';
}

/// HTTP client for the TrustLedger API with retries and exponential backoff.
class ApiClient {
  ApiClient({
    required this.baseUrl,
    this.apiKey = '',
    http.Client? client,
    this.maxAttempts = 3,
    this.baseDelay = const Duration(milliseconds: 400),
    this.timeout = const Duration(seconds: 30),
  }) : _http = client ?? http.Client();

  final String baseUrl;
  final String apiKey;
  final int maxAttempts;
  final Duration baseDelay;
  final Duration timeout;
  final http.Client _http;
  String? token;

  Map<String, String> _headers({bool json = true}) => {
    if (json) 'Content-Type': 'application/json',
    if (apiKey.isNotEmpty) 'X-API-Key': apiKey,
    if (token != null) 'Authorization': 'Bearer $token',
  };

  Future<dynamic> get(String path) => _send(() => _http.get(_uri(path), headers: _headers()));

  Future<dynamic> post(String path, [Object? body]) =>
      _send(() => _http.post(_uri(path), headers: _headers(), body: jsonEncode(body ?? {})));

  Future<dynamic> delete(String path) => _send(() => _http.delete(_uri(path), headers: _headers()));

  Future<dynamic> postFile(String path, Map<String, String> fields, List<int> bytes, String filename) =>
      _send(() async {
        final req = http.MultipartRequest('POST', _uri(path))
          ..headers.addAll(_headers(json: false))
          ..fields.addAll(fields)
          ..files.add(http.MultipartFile.fromBytes('file', bytes, filename: filename));
        return http.Response.fromStream(await _http.send(req));
      });

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  Future<dynamic> _send(Future<http.Response> Function() request) async {
    ApiException? last;
    for (var attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        final resp = await request().timeout(timeout);
        final body = resp.body.isEmpty ? null : jsonDecode(utf8.decode(resp.bodyBytes));
        if (resp.statusCode < 400) return body;
        final detail = body is Map ? (body['detail'] ?? body['error'] ?? '').toString() : resp.body;
        if (resp.statusCode >= 500) {
          last = ApiException('server', detail, status: resp.statusCode);
        } else if (resp.statusCode == 403 && body is Map && body['error'] == 'CONSENT_MISSING') {
          throw ApiException('consent', detail, status: 403);
        } else {
          throw ApiException('client', detail, status: resp.statusCode);
        }
      } on ApiException {
        rethrow;
      } on TimeoutException catch (e) {
        last = ApiException('network', e.toString());
      } on http.ClientException catch (e) {
        last = ApiException('network', e.message);
      } on FormatException catch (e) {
        last = ApiException('server', e.message);
      } catch (e) {
        // SocketException and other IO errors (dart:io is unavailable on web)
        last = ApiException('network', e.toString());
      }
      if (attempt < maxAttempts) {
        await Future<void>.delayed(baseDelay * (1 << (attempt - 1)));
      }
    }
    throw last!;
  }
}
