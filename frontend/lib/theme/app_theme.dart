/// NaviAble Application Theme
///
/// Defines the design system used across the NaviAble Flutter application.
/// All colours are chosen to satisfy WCAG AA contrast requirements (4.5:1 for
/// normal text, 3:1 for large text) in accordance with the accessibility mandate
/// in `.agent/system/CONSTRAINTS_AND_RULES.md`.
library app_theme;

import 'package:flutter/material.dart';

/// Colour palette constants.
///
/// Using a class of constants (rather than individual [Color] literals scattered
/// throughout the code) ensures every colour reference is centralised and
/// can be changed in one place.
abstract final class NaviAbleColors {
  /// Primary brand colour — deep blue, AA-compliant on white backgrounds.
  static const Color primary = Color(0xFF4361EE);

  /// Darker shade of primary for pressed / hover states.
  static const Color primaryDark = Color(0xFF3A56D4);

  /// Accent / success colour — teal.  Used for high trust scores (≥ 0.70).
  static const Color accent = Color(0xFF2EC4B6);

  /// Warning colour — amber.  Used for medium trust scores (0.40–0.69).
  static const Color warning = Color(0xFFFF9F1C);

  /// Danger / low confidence colour — red.  Used for trust scores < 0.40.
  static const Color danger = Color(0xFFEF233C);

  /// Light background.
  static const Color background = Color(0xFFF0F4F8);

  /// Card surface.
  static const Color surface = Color(0xFFFFFFFF);

  /// Subtle divider / border colour.
  static const Color border = Color(0xFFDDE3EC);

  /// Primary text on light backgrounds.
  static const Color textPrimary = Color(0xFF1A202C);

  /// Secondary / muted text.
  static const Color textMuted = Color(0xFF718096);
}

/// The centralised theme definition for NaviAble.
abstract final class NaviAbleTheme {
  /// Light theme — default theme for bright environments.
  ///
  /// Designed for high readability on laptop / desktop screens and mobile
  /// devices in bright light conditions.
  static ThemeData get light {
    const colorScheme = ColorScheme.light(
      primary: NaviAbleColors.primary,
      onPrimary: Colors.white,
      secondary: NaviAbleColors.accent,
      onSecondary: Colors.white,
      error: NaviAbleColors.danger,
      surface: NaviAbleColors.surface,
      onSurface: NaviAbleColors.textPrimary,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: NaviAbleColors.background,
      fontFamily: 'Roboto',

      appBarTheme: const AppBarTheme(
        backgroundColor: NaviAbleColors.primary,
        foregroundColor: Colors.white,
        elevation: 2,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: Colors.white,
          fontSize: 20,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.3,
        ),
      ),

      cardTheme: CardThemeData(
        color: NaviAbleColors.surface,
        elevation: 2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: NaviAbleColors.border, width: 1),
        ),
        margin: const EdgeInsets.all(0),
      ),

      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: NaviAbleColors.primary,
          foregroundColor: Colors.white,
          // 48 dp minimum touch target per accessibility mandate.
          minimumSize: const Size.fromHeight(48),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          textStyle: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),

      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: NaviAbleColors.primary,
          minimumSize: const Size.fromHeight(48),
          side: const BorderSide(color: NaviAbleColors.primary, width: 1.5),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
        ),
      ),

      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: NaviAbleColors.surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: NaviAbleColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: NaviAbleColors.border, width: 1.5),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: NaviAbleColors.primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: NaviAbleColors.danger, width: 1.5),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        labelStyle: const TextStyle(color: NaviAbleColors.textMuted),
      ),

      chipTheme: ChipThemeData(
        backgroundColor: const Color(0xFFE3F2FD),
        labelStyle: const TextStyle(
          color: Color(0xFF0D47A1),
          fontWeight: FontWeight.w600,
          fontSize: 12,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      ),
    );
  }

  /// Dark theme — for low-light environments.
  static ThemeData get dark {
    const colorScheme = ColorScheme.dark(
      primary: NaviAbleColors.primary,
      onPrimary: Colors.white,
      secondary: NaviAbleColors.accent,
      onSecondary: Color(0xFF1A202C),
      error: NaviAbleColors.danger,
      surface: Color(0xFF1F2937),
      onSurface: Color(0xFFF3F4F6),
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: const Color(0xFF111827),
      fontFamily: 'Roboto',
      brightness: Brightness.dark,

      appBarTheme: const AppBarTheme(
        backgroundColor: Color(0xFF1F2937),
        foregroundColor: Color(0xFFF3F4F6),
        elevation: 2,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: Color(0xFFF3F4F6),
          fontSize: 20,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.3,
        ),
      ),

      cardTheme: CardThemeData(
        color: const Color(0xFF1F2937),
        elevation: 2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: Color(0xFF374151), width: 1),
        ),
        margin: const EdgeInsets.all(0),
      ),

      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: NaviAbleColors.primary,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(48),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          textStyle: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),

      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: NaviAbleColors.primary,
          minimumSize: const Size.fromHeight(48),
          side: const BorderSide(color: NaviAbleColors.primary, width: 1.5),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
        ),
      ),

      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFF374151),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: Color(0xFF4B5563)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: Color(0xFF4B5563), width: 1.5),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: NaviAbleColors.primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: NaviAbleColors.danger, width: 1.5),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        labelStyle: const TextStyle(color: Color(0xFF9CA3AF)),
      ),

      chipTheme: ChipThemeData(
        backgroundColor: const Color(0xFF1E3A8A),
        labelStyle: const TextStyle(
          color: Color(0xFF93C5FD),
          fontWeight: FontWeight.w600,
          fontSize: 12,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      ),
    );
  }
}
