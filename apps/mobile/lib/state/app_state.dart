import 'package:flutter/foundation.dart';

import '../api/api_client.dart';
import '../api/trustledger_api.dart';
import '../l10n.dart';

const apiBaseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: 'http://localhost:8000');
const apiKey = String.fromEnvironment('API_KEY', defaultValue: 'dev-key');

/// App-wide state (language, borrower identity, latest decision, loan).
class AppState extends ChangeNotifier {
  AppState({TrustLedgerApi? api}) : api = api ?? TrustLedgerApi(ApiClient(baseUrl: apiBaseUrl, apiKey: apiKey));

  final TrustLedgerApi api;
  String lang = 'bn';
  String? userId;
  String? personaKey;
  String? group;
  Set<String> consents = {};
  List<String> sms = [];
  Map<String, dynamic>? lastDocument;
  Map<String, dynamic>? result; // POST /apply response
  Map<String, dynamic>? loan;
  double amount = 15000;

  String t(String key) => tr(key, lang);

  void toggleLanguage() {
    lang = lang == 'bn' ? 'en' : 'bn';
    notifyListeners();
  }

  Future<void> selectPersona(Map<String, dynamic> persona) async {
    userId = persona['user_id'] as String;
    personaKey = persona['key'] as String;
    group = persona['group'] as String?;
    amount = personaKey == 'shathi' ? 15000 : (personaKey == 'student' ? 5000 : 8000);
    result = null;
    loan = null;
    sms = [];
    lastDocument = null;
    await api.startSession(userId!);
    await refreshProfile();
  }

  Future<void> refreshProfile() async {
    final me = await api.me();
    consents = (me['consents'] as List).cast<String>().toSet();
    notifyListeners();
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

  Future<void> deleteAll() async {
    await api.deleteMe();
    userId = null;
    result = null;
    loan = null;
    consents = {};
    api.client.token = null;
    notifyListeners();
  }
}
