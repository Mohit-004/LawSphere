package in.lawsphere.desktop.service;

import in.lawsphere.desktop.api.AiServiceException;
import in.lawsphere.desktop.api.LocalAiClient;

import java.io.IOException;
import java.net.URISyntaxException;
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
        Path localDataDirectory = resolveLocalDataDirectory();
        Path logsDirectory = localDataDirectory.resolve("logs");
        Path logFile = logsDirectory.resolve("ai-engine.log");
        try {
            Files.createDirectories(logsDirectory);
            ProcessBuilder builder = new ProcessBuilder(buildCommand(engineDirectory));
            builder.directory(engineDirectory.toFile());
            builder.redirectErrorStream(true);
            builder.redirectOutput(logFile.toFile());
            Map<String, String> environment = builder.environment();
            environment.put("LAWSPHERE_DATABASE_PATH",
                    localDataDirectory.resolve("database").resolve("lawsphere.db").toString());
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

    private List<String> buildCommand(Path engineDirectory) {
        String configuredPython = System.getenv("LAWSPHERE_PYTHON_EXECUTABLE");
        String localAppData = System.getenv("LOCALAPPDATA");
        Path installedPython = localAppData == null || localAppData.isBlank()
                ? projectRoot.resolve("local-data").resolve("python-env")
                        .resolve("Scripts").resolve("python.exe")
                : Path.of(localAppData, "LawSphere", "python-env", "Scripts", "python.exe");
        Path virtualEnvPython = engineDirectory.resolve(".venv").resolve("Scripts").resolve("python.exe");
        String python = configuredPython != null && !configuredPython.isBlank()
                ? configuredPython
                : Files.isRegularFile(installedPython)
                        ? installedPython.toString()
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

        try {
            Path codeLocation = Path.of(AiEngineProcessManager.class.getProtectionDomain()
                    .getCodeSource().getLocation().toURI()).toAbsolutePath().normalize();
            Path candidate = Files.isRegularFile(codeLocation) ? codeLocation.getParent() : codeLocation;
            for (Path current = candidate; current != null; current = current.getParent()) {
                if (Files.isDirectory(current.resolve("ai-engine"))) {
                    return current;
                }
            }
        } catch (URISyntaxException | NullPointerException exception) {
            // Fall through to the working directory lookup for unusual class loaders.
        }

        for (Path current = Path.of("").toAbsolutePath().normalize();
             current != null;
             current = current.getParent()) {
            if (Files.isDirectory(current.resolve("ai-engine"))) {
                return current;
            }
        }
        throw new AiServiceException(
                "Could not locate the LawSphere project. Set LAWSPHERE_PROJECT_ROOT.");
    }

    private Path resolveLocalDataDirectory() {
        String localAppData = System.getenv("LOCALAPPDATA");
        Path directory = localAppData == null || localAppData.isBlank()
                ? projectRoot.resolve("local-data")
                : Path.of(localAppData, "LawSphere");
        try {
            Files.createDirectories(directory);
        } catch (IOException exception) {
            throw new AiServiceException("Could not create LawSphere user data directory " + directory, exception);
        }
        return directory;
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
