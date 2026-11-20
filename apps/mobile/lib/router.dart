import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'design/theme.dart';
import 'screens/bhorsha_chat_screen.dart';
import 'screens/connect_data_screen.dart';
import 'screens/consent_screen.dart';
import 'screens/loan_offer_screen.dart';
import 'screens/processing_screen.dart';
import 'screens/reasons_screen.dart';
import 'screens/repayment_screen.dart';
import 'screens/score_reveal_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/welcome_screen.dart';
import 'state/app_state.dart';
import 'widgets/responsive.dart';

/// Real URLs for every screen. Routes behind the session redirect to `/` when it is missing,
/// and routes that need a decision fall back to `/connect`.
abstract final class Routes {
  static const home = '/';
  static const consent = '/consent';
  static const connect = '/connect';
  static const processing = '/processing';
  static const score = '/score';
  static const reasons = '/reasons';
  static const loan = '/loan';
  static const repay = '/repay';
  static const bhorsha = '/bhorsha';
  static const settings = '/settings';
}

String? redirectFor(AppState state, String location) {
  if (location == Routes.home) return null;
  if (!state.hasSession) return Routes.home;
  const needsDecision = {Routes.score, Routes.reasons, Routes.loan};
  if (needsDecision.contains(location) && state.decision == null) return Routes.connect;
  if (location == Routes.repay && state.applicationId == null) return Routes.connect;
  return null;
}

GoRouter buildRouter(AppState state, {String initialLocation = Routes.home}) {
  GoRoute page(String path, Widget Function() screen, [double? maxWidth]) => GoRoute(
    path: path,
    pageBuilder: (context, _) => MaterialPage(
      key: ValueKey(path),
      child: ResponsiveFrame(
        maxWidth: maxWidth ?? TLayout.contentMaxWidth,
        child: screen(),
      ),
    ),
  );
  return GoRouter(
    initialLocation: initialLocation,
    refreshListenable: state,
    redirect: (context, s) => redirectFor(state, s.matchedLocation),
    routes: [
      page(Routes.home, () => WelcomeScreen(state: state)),
      page(Routes.consent, () => ConsentScreen(state: state)),
      page(Routes.connect, () => ConnectDataScreen(state: state)),
      page(Routes.processing, () => ProcessingScreen(state: state)),
      page(Routes.score, () => ScoreRevealScreen(state: state)),
      page(Routes.reasons, () => ReasonsScreen(state: state)),
      page(Routes.loan, () => LoanOfferScreen(state: state)),
      page(Routes.repay, () => RepaymentScreen(state: state), TLayout.wideContentMaxWidth),
      page(Routes.bhorsha, () => BhorshaChatScreen(state: state)),
      page(Routes.settings, () => SettingsScreen(state: state), TLayout.wideContentMaxWidth),
    ],
  );
}
