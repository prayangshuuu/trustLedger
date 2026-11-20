import 'package:flutter/material.dart';

/// TrustLedger palette: teal, navy, gold.
class TLColors {
  static const teal = Color(0xFF14B8A6);
  static const navy = Color(0xFF0F172A);
  static const gold = Color(0xFFF5B942);
  static const good = Color(0xFF16A34A);
  static const warn = Color(0xFFD97706);
  static const bad = Color(0xFFDC2626);
  static const surface = Color(0xFFF8FAFC);
}

ThemeData buildTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: TLColors.teal,
    primary: TLColors.teal,
    secondary: TLColors.gold,
    surface: TLColors.surface,
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    fontFamily: 'HindSiliguri',
    scaffoldBackgroundColor: TLColors.surface,
    appBarTheme: const AppBarTheme(backgroundColor: TLColors.navy, foregroundColor: Colors.white, centerTitle: false),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: TLColors.teal,
        minimumSize: const Size.fromHeight(52),
        textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600, fontFamily: 'HindSiliguri'),
      ),
    ),
    cardTheme: const CardThemeData(margin: EdgeInsets.symmetric(vertical: 6)),
  );
}

Color bandColor(String band) => switch (band) {
  'Excellent' => TLColors.good,
  'Good' => TLColors.teal,
  'Fair' => TLColors.gold,
  _ => TLColors.warn,
};
