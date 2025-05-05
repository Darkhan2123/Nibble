# Contribution Guidelines

This document outlines the process for contributing to the Nibble platform. We welcome contributions from all team members and value your input in making this platform better.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Pull Request Process](#pull-request-process)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Review Process](#review-process)

## Code of Conduct

All contributors are expected to adhere to our code of conduct. Please read [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) before contributing.

## Getting Started

1. **Setup Development Environment**
   - Follow the instructions in [Development Setup](./setup.md) to set up your local environment
   - Ensure Docker and Docker Compose are installed
   - Verify that you can run the project locally

2. **Find Issues to Work On**
   - Check the issue tracker for open issues
   - Look for issues labeled "good first issue" if you're new to the project
   - If you want to work on something not in the issue tracker, create a new issue first

3. **Understand the Architecture**
   - Review the [Architecture Documentation](../architecture/README.md) to understand the system design
   - Familiarize yourself with the [API Documentation](../api/README.md)

## Development Workflow

We follow a feature branch workflow:

1. **Create a Feature Branch**
   ```bash
   git checkout main
   git pull
   git checkout -b feature/your-feature-name
   ```

2. **Make Your Changes**
   - Write your code following the [Coding Standards](#coding-standards)
   - Add tests for new functionality
   - Update documentation as needed

3. **Commit Your Changes**
   - Write clear, concise commit messages
   - Reference issue numbers in commit messages
   - Use present tense ("Add feature" not "Added feature")
   ```bash
   git commit -m "Add user profile validation #123"
   ```

4. **Push Your Branch**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request**
   - Create a pull request against the main branch
   - Fill out the pull request template
   - Request reviews from relevant team members

## Coding Standards

### Python Code Style

We follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide with these additional guidelines:

1. **Code Formatting**
   - Use [Black](https://black.readthedocs.io/) for code formatting
   - Use [isort](https://pycqa.github.io/isort/) for import sorting
   - Max line length: 88 characters (Black default)

2. **Type Annotations**
   - Use type annotations for all function parameters and return values
   - Use [mypy](http://mypy-lang.org/) for type checking

3. **Documentation**
   - All public functions, classes, and modules should have docstrings
   - Follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) for docstrings

4. **Linting**
   - Code should pass [flake8](https://flake8.pycqa.org/) checks
   - Run linters before submitting pull requests

### SQL Style

1. **Formatting**
   - Keywords in UPPERCASE (SELECT, FROM, WHERE, etc.)
   - Table and column names in snake_case
   - Indentation: 4 spaces

2. **Naming Conventions**
   - Tables: Singular noun (e.g., `user` not `users`)
   - Junction tables: Combine both table names (e.g., `user_role`)
   - Primary keys: `id`
   - Foreign keys: `entity_id` (e.g., `user_id`)

3. **Schema Organization**
   - Each service has its own schema prefix (e.g., `user_service.users`)
   - Include appropriate comments for complex constraints or indexes

### Code Organization

1. **Project Structure**
   - Follow the established structure for each microservice
   - Place related functionality in appropriate modules
   - Avoid circular dependencies

2. **Dependency Management**
   - All dependencies must be declared in requirements.txt
   - Pin dependency versions for reproducibility
   - Minimize external dependencies when possible

## Pull Request Process

1. **Before Submitting**
   - Ensure all tests pass locally
   - Run linters and formatters
   - Update documentation if needed
   - Squash or rebase commits if necessary

2. **PR Template**
   - Use the provided pull request template
   - Fill out all sections completely
   - Link related issues

3. **Review Process**
   - At least one review is required before merging
   - Address all review comments
   - Request additional reviews if needed

4. **Merge Requirements**
   - All CI checks must pass
   - Required reviews must be approved
   - No unresolved conversations
   - PR must be up to date with the main branch

## Testing Guidelines

1. **Test Coverage**
   - All new code should have tests
   - Target test coverage: 80% or higher
   - Both unit tests and integration tests are valuable

2. **Test Organization**
   - Tests should be in a separate `tests` directory
   - Test files should mirror the structure of the code they test
   - Use clear, descriptive test names

3. **Test Types**
   - **Unit Tests**: Test individual functions and classes
   - **Integration Tests**: Test interactions between components
   - **API Tests**: Test API endpoints
   - **Database Tests**: Test database interactions

4. **Testing Tools**
   - [pytest](https://docs.pytest.org/) for running tests
   - [pytest-cov](https://pytest-cov.readthedocs.io/) for coverage reports
   - [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio) for testing async code

## Documentation

1. **Types of Documentation**
   - **Code Documentation**: Docstrings and comments
   - **API Documentation**: OpenAPI specifications
   - **Architecture Documentation**: Design decisions and diagrams
   - **User Documentation**: How to use the platform

2. **Documentation Guidelines**
   - Keep documentation up to date with code changes
   - Use clear, concise language
   - Include examples where appropriate
   - Update diagrams when architecture changes

3. **Documentation Locations**
   - Code documentation: In the code itself
   - API documentation: In OpenAPI specifications
   - Architecture documentation: In the `/docs/architecture/` directory
   - User documentation: In the `/docs/user/` directory

## Review Process

1. **Code Review Guidelines**
   - Focus on code quality, readability, and correctness
   - Check for potential bugs and edge cases
   - Ensure tests cover the changes
   - Verify documentation is updated

2. **Reviewer Responsibilities**
   - Be respectful and constructive
   - Provide specific feedback
   - Suggest alternatives when rejecting code
   - Respond to review requests promptly

3. **Author Responsibilities**
   - Be open to feedback
   - Respond to reviewer comments
   - Make requested changes or explain why they are not needed
   - Ask for clarification if review comments are unclear

## Continuous Integration

Our CI pipeline runs these checks on all pull requests:

1. **Linting and Formatting**
   - Black code formatting check
   - isort import sorting check
   - flake8 linting check
   - mypy type checking

2. **Testing**
   - Run all tests
   - Calculate test coverage
   - Fail if coverage decreases significantly

3. **Security Checks**
   - Dependency vulnerability scanning
   - Code security analysis

4. **Build and Deploy**
   - Build Docker images
   - Run integration tests
   - Deploy to staging environment (for PRs to main)

## Additional Resources

- [Development Setup Guide](./setup.md)
- [Debugging Guide](./debugging.md)
- [Performance Optimization Guide](./performance.md)
- [Security Best Practices](./security.md)
- [Database Migration Guide](./database-migrations.md)

## Questions and Support

If you have questions about contributing, please:
1. Check the documentation
2. Ask in the development channel
3. Create an issue labeled "question"

We appreciate your contributions and look forward to your involvement in improving the Nibble platform!