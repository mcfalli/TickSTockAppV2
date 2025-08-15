# TickStock Documentation

## Overview

TickStock is a real-time market data processing and visualization application that handles live stock market data from 4,000+ tickers. The system processes data through sophisticated event detection algorithms to identify trading patterns and delivers personalized data streams to authenticated users.

## Quick Links

### Core Documentation
- [System Architecture](architecture/system-architecture.md) - High-level system design and components
- [Data Flow Pipeline](architecture/data-flow-pipeline.md) - How data moves through the system
- [Component Architecture](architecture/component-architecture.md) - Detailed component specifications

### API Documentation
- [WebSocket Events](api/websocket-events.md) - Real-time event specifications
- [REST Endpoints](api/rest-endpoints.md) - HTTP API reference

### Development Guides
- [Quick Start Guide](development/quick-start.md) - Get running in 5 minutes
- [Testing Guide](development/testing-guide.md) - Testing strategies and patterns
- [Coding Standards](development/coding-standards.md) - Style guide and best practices

### Operations
- [Deployment Guide](operations/deployment.md) - Production deployment procedures
- [Monitoring Guide](operations/monitoring.md) - Health checks and metrics

## System Overview

TickStock consists of 17 specialized components organized into four functional groups:

1. **Core Processing Components (6)** - Heart of the data pipeline
2. **Event Processing Components (3)** - Event detection and prioritization  
3. **Universe Management Components (4)** - User preferences and filtering
4. **Data Flow Components (4)** - Data preparation and monitoring

### Key Features

- **Real-time Processing**: Sub-millisecond tick processing
- **Dual Universe Architecture**: Core universe (2,800 stocks) for analytics, user universe (800 stocks) for display
- **Per-User Personalization**: Individual universe selection and filtering
- **Memory-First Architecture**: 500:1 database write efficiency
- **Scalable Worker Pool**: Dynamic scaling from 2-16 workers
- **Comprehensive Monitoring**: Health checks, metrics, and performance tracking

## Navigation Guide

### For New Developers
1. Start with the [Quick Start Guide](development/quick-start.md)
2. Review the [System Architecture](architecture/system-architecture.md)
3. Understand the [Data Flow Pipeline](architecture/data-flow-pipeline.md)
4. Explore specific components in [Component Architecture](architecture/component-architecture.md)

### For API Integration
1. Review [WebSocket Events](api/websocket-events.md) for real-time data
2. Check [REST Endpoints](api/rest-endpoints.md) for configuration APIs
3. See authentication requirements in the respective API docs

### For Operations
1. Follow the [Deployment Guide](operations/deployment.md)
2. Set up monitoring per the [Monitoring Guide](operations/monitoring.md)
3. Review performance benchmarks in System Architecture

## Documentation Standards

All documentation follows these principles:
- **Current State**: Documents describe the system as it exists today
- **Clear Examples**: Code examples for complex concepts
- **Practical Focus**: How to use and operate the system
- **Maintenance**: Regular updates with each sprint

## Contributing to Documentation

When updating documentation:
1. Follow the established format and style
2. Include code examples where helpful
3. Update the relevant index sections
4. Keep focus on current system state
5. Review the [Documentation Checklist](DOCUMENTATION_CHECKLIST.md)

## Support

For questions about the documentation or system:
- Check the relevant documentation section first
- Review the FAQ (if applicable)
- Contact the development team

---
*Last Updated: June 2025*