package com.ericsson.nms.eniq.test_app;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketException;
import java.util.Map;
import java.util.TreeMap;

public class MainClassServer {

  static {
    Runtime.getRuntime().addShutdownHook(new Thread() {
      @Override
      public void run() {
        System.out.println("Shutting down from:");
        for (StackTraceElement ste : Thread.currentThread().getStackTrace()) {
          System.out.println(ste.toString());
        }
      }
    });
  }

  private final ServerSocket serverSocket;

  public MainClassServer() throws IOException {
    this.serverSocket = new ServerSocket(55000);
  }

  public static void main(String[] args) throws IOException {
    final MainClassServer mc = new MainClassServer();
    mc.accept();
  }

  public void accept() {
    while (true) {
      final Socket s;
      try {
        s = this.serverSocket.accept();
      } catch (SocketException e) {
        break;
      } catch (IOException e) {
        e.printStackTrace();
        continue;
      }
      final Thread t = new Thread() {
        @Override
        public void run() {
          try {
            final BufferedReader in = new BufferedReader(new InputStreamReader(s.getInputStream()));
            String cmd;
            while ((cmd = in.readLine()) != null) {
              if (cmd.equalsIgnoreCase("exit") || cmd.equalsIgnoreCase("quit")) {
                exit();
              } else if (cmd.equalsIgnoreCase("properties")) {
                final TreeMap<String, String> map = new TreeMap<>();
                for (Map.Entry<Object, Object> entry : System.getProperties().entrySet()) {
                  map.put(entry.getKey().toString(), entry.getValue().toString());
                }
                for (Map.Entry<String, String> entry : map.entrySet()) {
                  System.out.println(entry.getKey() + " -> " + entry.getValue());
                }
              } else {
                System.out.println("Server revieved " + cmd);
              }
            }
          } catch (Throwable t) {
            t.printStackTrace();
          }
        }
      };
      t.setDaemon(true);
      t.start();
    }
  }

  public void exit() {
    try {
      this.serverSocket.close();
    } catch (Throwable e) {/**/}
    System.out.println("Exiting ...");
    System.exit(0);
  }
}
