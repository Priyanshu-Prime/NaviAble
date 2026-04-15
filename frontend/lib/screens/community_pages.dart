library community_pages;

import 'package:flutter/material.dart';

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return _InfoScaffold(
      title: 'About NaviAble',
      sections: const [
        _InfoSection(
          heading: 'What we are building',
          body:
              'NaviAble is a community-driven accessibility verification platform. '
              'People can submit photos and reviews, and our Dual-AI backend '
              'scores confidence for accessibility claims.',
        ),
        _InfoSection(
          heading: 'How this app works today',
          body:
              'The current Flutter frontend supports backend health checks and '
              'the complete verification flow with POST /api/v1/verify.',
        ),
        _InfoSection(
          heading: 'Community vision',
          body:
              'The React prototype includes broader discovery features '
              '(explore, profiles, and location feeds). Those are planned '
              'for phased integration as matching backend APIs are added.',
        ),
      ],
    );
  }
}

class AccessibilityGuideScreen extends StatelessWidget {
  const AccessibilityGuideScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return _InfoScaffold(
      title: 'Accessibility Guide',
      sections: const [
        _InfoSection(
          heading: 'Wheelchair access',
          body:
              'Look for step-free paths, wide entrances, and interior circulation '
              'without narrow choke points.',
        ),
        _InfoSection(
          heading: 'Ramps and handrails',
          body:
              'Prefer gentle slopes, non-slip surfaces, and handrails on both '
              'sides where possible.',
        ),
        _InfoSection(
          heading: 'Elevator and restroom access',
          body:
              'Check reachable elevator controls, clear maneuvering space, '
              'and restroom layouts that support wheelchair turning radius.',
        ),
        _InfoSection(
          heading: 'Assistive signage and hearing support',
          body:
              'Braille signage, tactile cues, high contrast labels, and hearing '
              'loop support all improve inclusive navigation.',
        ),
      ],
    );
  }
}

class PrivacyPolicyScreen extends StatelessWidget {
  const PrivacyPolicyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return _InfoScaffold(
      title: 'Privacy Policy',
      sections: const [
        _InfoSection(
          heading: 'Data you submit',
          body:
              'Reviews, uploaded photos, and related metadata are sent to the '
              'backend to run verification and display results.',
        ),
        _InfoSection(
          heading: 'How data is used',
          body:
              'Submitted data is used to operate verification features and '
              'improve system quality. Public contribution features are still '
              'being phased in.',
        ),
        _InfoSection(
          heading: 'Security and retention',
          body:
              'Use production-grade API hosting and transport security when '
              'deploying. Define your retention and deletion policies before '
              'enabling user accounts.',
        ),
      ],
    );
  }
}

class _InfoScaffold extends StatelessWidget {
  const _InfoScaffold({required this.title, required this.sections});

  final String title;
  final List<_InfoSection> sections;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 900),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 16),
                for (final section in sections) ...[
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            section.heading,
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          const SizedBox(height: 8),
                          Text(section.body),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _InfoSection {
  const _InfoSection({required this.heading, required this.body});

  final String heading;
  final String body;
}

