import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trustledger_app/api/api_client.dart';
import 'package:trustledger_app/api/trustledger_api.dart';
import 'package:trustledger_app/main.dart';
import 'package:trustledger_app/state/app_state.dart';

/// A fake API backend recording every request.
class FakeBackend {
  final requests = <http.Request>[];
  final consents = <String>{};

  http.Response _json(Object body, [int status = 200]) =>
      http.Response.bytes(utf8.encode(jsonEncode(body)), status, headers: {'content-type': 'application/json'});

  Future<http.Response> handle(http.Request req) async {
    requests.add(req);
    final path = req.url.path;
    if (path == '/demo/personas') {
      return _json([
        {'key': 'moon', 'user_id': 'u1', 'group': 'F_urban', 'division': 'Dhaka', 'description': 'Moon'},
      ]);
    }
    if (path == '/auth/session') return _json({'token': 'tl1.u1.9999999999.sig', 'expires_at': 1, 'user_id': 'u1'});
    if (path == '/me' && req.method == 'GET') {
      return _json({'user_id': 'u1', 'group': 'F_urban', 'division': 'Dhaka', 'consents': consents.toList()});
    }
    if (path == '/consent' && req.method == 'POST') {
      consents.add((jsonDecode(req.body) as Map)['source'] as String);
      return _json({'status': 'granted'}, 201);
    }
    if (path.startsWith('/consent/') && req.method == 'DELETE') {
      consents.remove(path.split('/').last);
      return _json({'status': 'revoked'});
    }
    if (path.startsWith('/bhorsha/start') || path == '/bhorsha/start') {
      return _json({
        'session_id': 'b1',
        'turn': 1,
        'total_turns': 12,
        'dimension': 'savings',
        'question_text': 'আপনার জরুরি প্রয়োজনের জন্য প্রতি মাসে কিছু টাকা আলাদা করে সরিয়ে রাখার অভ্যাস আছে কি?',
        'english_translation': 'Do you have a regular habit of setting aside money each month for emergencies?',
      });
    }
    if (path == '/me' && req.method == 'DELETE') return _json({'status': 'deleted'});
    return _json({'detail': 'not found'}, 404);
  }

  AppState state() => AppState(
    api: TrustLedgerApi(ApiClient(baseUrl: 'http://test', client: MockClient(handle), baseDelay: Duration.zero)),
  );
}

Map<String, dynamic> moonResult() => {
  'trace_id': 't1',
  'status': 'approved',
  'summary_bn': 'আপনার ট্রাস্টলেজার স্কোর ৬৯১।',
  'grounded_tips': [
    {
      'feature': 'savings_ratio',
      'text': 'প্রতি মাসে আয়ের অন্তত ৫% সঞ্চয় করুন।',
      'source': {'title': 'ট্রাস্টলেজার স্কোর নির্দেশিকা', 'url': 'x', 'excerpt': 'y'},
    },
  ],
  'trace': [],
  'decision': {
    'decision_id': 'd1',
    'application_id': 'a1',
    'score': 691,
    'band': 'Good',
    'p_repay': 0.934,
    'approved': true,
    'reasons': [
      {
        'feature': 'bills_on_time',
        'label': 'Bills paid on time',
        'text': 'বিল সময়মতো পরিশোধ',
        'impact': 0.9,
        'kind': 'good',
      },
      {'feature': 'savings_ratio', 'label': 'Savings ratio', 'text': 'সঞ্চয় কম', 'impact': -0.1, 'kind': 'bad'},
    ],
  },
};

/// A signed-in Moon state backed by [FakeBackend], optionally with her decision loaded.
Future<AppState> signedIn(FakeBackend backend, {bool withResult = false}) async {
  final state = backend.state();
  await state.selectPersona({'user_id': 'u1', 'key': 'moon', 'group': 'F_urban'});
  if (withResult) state.result = moonResult();
  return state;
}

/// Pump the real app (router, theme, responsive frame) at [location].
Future<void> pumpApp(WidgetTester tester, AppState state, String location, {Size size = const Size(390, 844)}) async {
  tester.view.physicalSize = size * 3;
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(TrustLedgerApp(state: state, initialLocation: location));
  await tester.pumpAndSettle();
}
