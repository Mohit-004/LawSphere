package in.lawsphere.desktop.service;

import in.lawsphere.desktop.api.AiServiceException;
import in.lawsphere.desktop.api.LocalAiClient;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/** Starts the local Python API when needed and owns only the process it launches. */
public final class AiEngineProcessManager implements AutoCloseable {
    private static final Duration STARTUP_TIMEOUT = Duration.ofSeconds(25);
    private static final Duration SHUTDOWN_TIMEOUT = Duration.ofSeconds(3);

    private final LocalAiClient client;
    private final Path projectRoot;
    private Process process;

    public AiEngineProcessManager(LocalAiClient client) {
        this.client = client;
        this.projectRoot = resolveProjectRoot();
    }

    public void startIfNeeded() {
        if (isApiAvailable()) {
            return;
        }

        Path engineDirectory = projectRoot.resolve("ai-engine");
        Path logsDirectory = projectRoot.resolve("local-data").resolve("logs");
        Path logFile = logsDirectory.resolve("ai-engine.log");
        try {
            Files.createDirectories(logsDirectory);
            ProcessBuilder builder = new ProcessBuilder(buildCommand(engineDirectory));
            builder.directory(engineDirectory.toFile());
            builder.redirectErrorStream(true);
            builder.redirectOutput(logFile.toFile());
            Map<String, String> environment = builder.environment();
            environment.put("LAWSPHERE_HOST", "127.0.0.1");
            environment.put("LAWSPHERE_PORT", "8000");
            process = builder.start();
        } catch (IOException exception) {
            throw new AiServiceException(
                    "Could not start the Python AI service. Check Python setup and " + logFile, exception);
        }

        Instant deadline = Instant.now().plus(STARTUP_TIMEOUT);
        while (Instant.now().isBefore(deadline)) {
            if (isApiAvailable()) {
                return;
            }
            if (!process.isAlive()) {
                int exitCode = process.exitValue();
                close();
                throw new AiServiceException(
                        "Python AI service exited with code " + exitCode + ". See " + logFile);
            }
            pauseBeforeRetry();
        }

        close();
        throw new AiServiceException(
                "Python AI service did not become ready within " + STARTUP_TIMEOUT.toSeconds()
                        + " seconds. See " + logFile);
    }

    private boolean isApiAvailable() {
        try {
            return "ok".equals(client.getSystemStatus().status());
        } catch (AiServiceException exception) {
            return false;
        }
    }

    private static List<String> buildCommand(Path engineDirectory) {
        String configuredPython = System.getenv("LAWSPHERE_PYTHON_EXECUTABLE");
        Path virtualEnvPython = engineDirectory.resolve(".venv").resolve("Scripts").resolve("python.exe");
        String python = configuredPython != null && !configuredPython.isBlank()
                ? configuredPython
                : Files.isRegularFile(virtualEnvPython) ? virtualEnvPython.toString() : "python";
        return List.of(
                python, "-m", "uvicorn", "app.main:app",
                "--host", "127.0.0.1", "--port", "8000");
    }

    private static Path resolveProjectRoot() {
        String configuredRoot = System.getenv("LAWSPHERE_PROJECT_ROOT");
        if (configuredRoot != null && !configuredRoot.isBlank()) {
            return Path.of(configuredRoot).toAbsolutePath().normalize();
        }

        Path current = Path.of("").toAbsolutePath().normalize();
        if (Files.isDirectory(current.resolve("ai-engine"))) {
            return current;
        }
        Path parent = current.getParent();
        if (parent != null && Files.isDirectory(parent.resolve("ai-engine"))) {
            return parent;
        }
        throw new AiServiceException(
                "Could not locate the LawSphere project. Set LAWSPHERE_PROJECT_ROOT.");
    }

    private void pauseBeforeRetry() {
        try {
            Thread.sleep(300);
        } catch (InterruptedException exception) {
            close();
            Thread.currentThread().interrupt();
            throw new AiServiceException("Interrupted while waiting for the Python AI service", exception);
        }
    }

    @Override
    public void close() {
        if (process == null || !process.isAlive()) {
            return;
        }
        process.destroy();
        try {
            if (!process.waitFor(SHUTDOWN_TIMEOUT.toMillis(), TimeUnit.MILLISECONDS)) {
                process.destroyForcibly();
                process.waitFor(SHUTDOWN_TIMEOUT.toMillis(), TimeUnit.MILLISECONDS);
            }
        } catch (InterruptedException exception) {
            process.destroyForcibly();
            Thread.currentThread().interrupt();
        }
        process = null;
    }
}
