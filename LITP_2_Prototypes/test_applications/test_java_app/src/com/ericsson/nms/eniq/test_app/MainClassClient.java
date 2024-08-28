package com.ericsson.nms.eniq.test_app;


import java.io.IOException;
import java.io.PrintWriter;
import java.net.Socket;

public class MainClassClient {
  public static void main(String[] args) throws IOException {
    final int serverPort = Integer.valueOf(args[0]);
    final String command = args[1];
    final Socket clientSocket = new Socket("localhost", serverPort);
    final PrintWriter out = new PrintWriter(clientSocket.getOutputStream(), true);
    System.out.println("Sending command '" + command + "' to server");
    out.println(command);
  }
}
