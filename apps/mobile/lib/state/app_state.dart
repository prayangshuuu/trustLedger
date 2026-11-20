import 'package:flutter/foundation.dart';

import '../api/api_client.dart';
import '../api/trustledger_api.dart';
import '../l10n.dart';
import '../platform/web_bridge.dart';

const _apiBaseDefine = String.fromEnvironment('API_BASE_URL', defaultValue: '');
const apiKey = String.fromEnvironment('API_KEY', defaultValue: 'dev-key');

/// API origin. An empty API_BASE_URL on web means "same origin" (the API serves the web app).
String resolveApiBase() {
  if (kIsWeb && _apiBaseDefine.isEmpty) {
    return Uri.base.origin;
  }
  return _apiBaseDefine.isEmpty ? 'http://localhost:8000' : _apiBaseDefine;
}

const _kUser = 'tl.user';
const _kPersona = 'tl.persona';
const _kAmount = 'tl.amount';
const _kLang = 'tl.lang';

/// App-wide state (language, borrower identity, latest decision, loan).
///
/// The bearer token lives only in memory. On the web the tab keeps the (pseudonymous) user id so
/// a reload can open a new session; nothing sensitive is written to browser storage.
class AppState extends ChangeNotifier {
  AppState({TrustLedgerApi? api}) : api = api ?? TrustLedgerApi(ApiClient(baseUrl: resolveApiBase(), apiKey: apiKey));

  final TrustLedgerApi api;
  String lang = 'bn';
  String? userId;
  String? personaKey;
  String? group;
  Set<String> consents = {};
  List<String> sms = [];
  Map<String, dynamic>? lastDocument;
  Map<String, dynamic>? result; // POST /apply response (or a restored equivalent)
  Map<String, dynamic>? loan;
  double amount = 15000;

  String t(String key) => tr(key, lang);

  bool get hasSession => userId != null && api.client.token != null;

  void toggleLanguage() {
    lang = lang == 'bn' ? 'en' : 'bn';
    sessionSet(_kLang, lang);
    notifyListeners();
  }

  Future<void> selectPersona(Map<String, dynamic> persona) async {
    userId = persona['user_id'] as String;
    personaKey = persona['key'] as String;
    group = persona['group'] as String?;
    amount = switch (personaKey) {
      'moon' => 15000,
      'student' => 5000,
      _ => 8000,
    };
    result = null;
    loan = null;
    sms = [];
    lastDocument = null;
    await api.startSession(userId!);
    _persist();
    await refreshProfile();
  }

  void _persist() {
    sessionSet(_kUser, userId);
    sessionSet(_kPersona, personaKey);
    sessionSet(_kAmount, userId == null ? null : amount.toString());
  }

  /// After a browser reload: open a fresh session for the same user and reload their state.
  Future<void> restore() async {
    lang = sessionGet(_kLang) ?? lang;
    final saved = sessionGet(_kUser);
    if (saved == null) return;
    try {
      userId = saved;
      personaKey = sessionGet(_kPersona);
      amount = double.tryParse(sessionGet(_kAmount) ?? '') ?? amount;
      await api.startSession(saved);
      final me = await refreshProfile();
      final latest = me['latest_decision'] as Map<String, dynamic>?;
      if (latest != null) await _restoreDecision(latest);
    } catch (_) {
      userId = null;
      api.client.token = null;
      _persist();
    }
    notifyListeners();
  }

  Future<void> _restoreDecision(Map<String, dynamic> latest) async {
    final explain = await api.explain(latest['decision_id'] as String);
    final reasons = (explain['reasons'] as List).cast<Map<String, dynamic>>();
    final status = latest['status'] as String? ?? (latest['approved'] == true ? 'approved' : 'rejected');
    result = {
      'status': status == 'disbursed' || status == 'repaid' ? 'approved' : status,
      'trace': <dynamic>[],
      'summary_bn': null,
      'grounded_tips': [
        for (final tip in (explain['tips'] as List).cast<String>()) {'feature': '', 'text': tip, 'source': null},
      ],
      'decision': {
        ...latest,
        'reasons': reasons,
        'good': explain['good'],
        'bad': explain['bad'],
        'tips': explain['tips'],
      },
    };
    if (latest['application_id'] != null && (status == 'disbursed' || status == 'repaid')) {
      await refreshLoan();
    }
  }

  Future<Map<String, dynamic>> refreshProfile() async {
    final me = await api.me();
    consents = (me['consents'] as List).cast<String>().toSet();
    group = me['group'] as String? ?? group;
    notifyListeners();
    return me;
  }

  Future<void> saveConsents(Set<String> wanted) async {
    for (final source in wanted.difference(consents)) {
      await api.grantConsent(userId!, source);
    }
    for (final source in consents.difference(wanted)) {
      await api.revokeConsent(source);
    }
    await refreshProfile();
  }

  Future<Map<String, dynamic>> runApply() async {
    result = await api.apply(userId!, amount, sms: sms.isEmpty ? null : sms);
    notifyListeners();
    return result!;
  }

  Map<String, dynamic>? get decision => result?['decision'] as Map<String, dynamic>?;

  String? get applicationId => decision?['application_id'] as String?;

  Future<void> refreshLoan() async {
    if (applicationId == null) return;
    loan = await api.loan(applicationId!);
    notifyListeners();
  }

  void signOut() {
    userId = null;
    personaKey = null;
    result = null;
    loan = null;
    consents = {};
    api.client.token = null;
    _persist();
    notifyListeners();
  }

  Future<void> deleteAll() async {
    await api.deleteMe();
    signOut();
  }
}
